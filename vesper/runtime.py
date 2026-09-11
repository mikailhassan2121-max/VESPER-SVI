import asyncio
import json
from collections import deque
from datetime import timedelta

import pandas as pd

from vesper.calendar import NY, Calendar, utcnow
from vesper.context import dated_records, load_history
from vesper.decision import decide, rank_predictions
from vesper.features import build_features, daily_features, normalize_bars
from vesper.forward import forward_summary, performance_pause, resolve_shadow, write_result
from vesper.market_state import enrich_candidates
from vesper.provider import Massive, timestamp_ms
from vesper.readiness import clock_check, feed_evidence
from vesper.registry import load_production
from vesper.storage import Store
from vesper.telegram import Telegram, signal_text
from vesper.universe import reference_universe


class Runtime:
    def __init__(self, settings, mode="LIVE"):
        if mode not in {"LIVE", "REPLAY"}:
            raise ValueError("Unsupported runtime mode")
        self.mode = mode
        self.settings = settings
        settings.prepare()
        self.calendar = Calendar()
        self.provider = Massive(settings.massive_api_key.get_secret_value())
        self.store = Store(settings.data_dir / ("vesper.sqlite" if mode == "LIVE" else "replay.sqlite"))
        self.queue = asyncio.Queue(maxsize=settings.queue_size)
        self.bars, self.quotes, self.luld = {}, {}, {}
        self.tasks = []
        self.model = None
        self.universe = {}
        self.ranked = pd.DataFrame()
        self.stop_event = asyncio.Event()
        self.status = {"mode": mode, "decision": "NO SIGNAL — SYSTEM INVALID", "failures": [],
                       "leaderboard": [], "production_validated": False, "universe": 0}
        self.daily = normalize_bars([], "")
        self.profiles, self.sectors = {}, {}
        self.news = None
        self.history = None
        self.history_day = None
        self.context_minute = None
        self.news_seen = {}
        self.last_news_success = None
        self.last_consumed = None
        self.backfill_done = None
        self.record_buffer = []
        self.telegram = Telegram(settings, self.store, self.status)
        self.eligible = set()
        self.stream_bars, self.trades = {}, {}
        self.market_status = None
        self.market_status_received = None
        self.clock_evidence = {"valid": False}
        self.earnings_tickers = set()
        self.earnings_received = None
        self.monitored = set()

    async def start(self):
        if self.mode != "LIVE":
            raise ValueError("Replay does not start live workers")
        try:
            self.model = load_production(self.settings.model_dir)
        except (OSError, ValueError, KeyError):
            self.status["failures"].append("PRODUCTION_MODEL_UNAVAILABLE")
        self.status["model"] = ({"model_id": self.model.metadata.get("model_id"), "status": "PRODUCTION"}
                                if self.model else {"status": "UNAVAILABLE"})
        self.tasks = [asyncio.create_task(self.supervise("reference", self.reference_worker)),
                      asyncio.create_task(self.provider.stream(self.queue)),
                      asyncio.create_task(self.supervise("consumer", self.consume)),
                      asyncio.create_task(self.supervise("news", self.news_worker)),
                      asyncio.create_task(self.supervise("market_status", self.market_status_worker)),
                      asyncio.create_task(self.supervise("earnings", self.earnings_worker)),
                      asyncio.create_task(self.supervise("backfill", self.backfill_worker)),
                      asyncio.create_task(self.supervise("recorder", self.recorder_worker)),
                      asyncio.create_task(self.supervise("retention", self.retention_worker)),
                      asyncio.create_task(self.telegram.delivery()),
                      asyncio.create_task(self.telegram.commands()),
                      asyncio.create_task(self.supervise("forward", self.forward_worker)),
                      asyncio.create_task(self.supervise("position_monitor", self.position_monitor_worker)),
                      asyncio.create_task(self.supervise("ranker", self.ranking_worker))]

    async def supervise(self, name, worker):
        while True:
            try:
                await worker()
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                code = f"{name.upper()}_{type(exc).__name__}"
                if code not in self.status["failures"]:
                    self.status["failures"].append(code)
                self.store.event("worker_failure", {"worker": name, "error": type(exc).__name__})
                await asyncio.sleep(10)

    def worker_recovered(self, name):
        prefix = name.upper()+"_"
        self.status["failures"] = [code for code in self.status["failures"] if not code.startswith(prefix)]

    async def reference_worker(self):
        current_day = None
        while True:
            day = utcnow().astimezone(NY).date()
            if day != current_day:
                references = await self.provider.references(day)
                self.universe, rejected = reference_universe(references)
                self.history = await asyncio.to_thread(load_history, self.settings.data_dir, day)
                self.history_day = day
                self.context_minute = None
                self.status.update(universe=len(self.universe), rejected=rejected)
                self.store.event("universe", {"date": str(day), "tickers": list(self.universe), "rejected": rejected})
                current_day = day
                self.worker_recovered("reference")
            await asyncio.sleep(60)

    async def news_worker(self):
        while True:
            now = utcnow()
            articles = await self.provider.news(now, now - timedelta(hours=24))
            received = utcnow()
            for article in articles:
                identity = article.get("id") or article.get("article_url")
                if identity and identity not in self.news_seen:
                    self.news_seen[identity] = article | {"available_at": received.isoformat()}
            self.news_seen = {key: value for key, value in self.news_seen.items()
                              if pd.Timestamp(value["published_utc"]) >= now - timedelta(hours=24)}
            self.news = list(self.news_seen.values())
            self.last_news_success = received
            self.worker_recovered("news")
            await asyncio.sleep(60)

    async def market_status_worker(self):
        while True:
            start = utcnow()
            status = await self.provider.market_status()
            received = utcnow()
            self.clock_evidence = clock_check(status, start, received)
            self.market_status, self.market_status_received = status, received
            self.worker_recovered("market_status")
            await asyncio.sleep(30)

    async def earnings_worker(self):
        while True:
            now = utcnow()
            session = self.calendar.session(now.astimezone(NY).date()) or self.calendar.upcoming(now)
            rows = await self.provider.earnings(session.day, session.next_day)
            # Conservative whole-day exclusion includes uncertain earnings times.
            self.earnings_tickers = {row["ticker"] for row in rows if row.get("ticker")}
            self.earnings_received = utcnow()
            self.worker_recovered("earnings")
            await asyncio.sleep(60)

    async def backfill_worker(self):
        """REST warms today's missing history while the stream keeps collecting updates."""
        while True:
            now = utcnow()
            session = self.calendar.session(now.astimezone(NY).date())
            if session and session.open <= now < session.close and self.universe and self.backfill_done != session.day:
                tickers = sorted(set(self.universe) | {"SPY", "QQQ", "IWM"})
                async def fetch(ticker):
                    raw = await self.provider.bars(ticker, session.day, session.day)
                    received = utcnow()
                    bars = normalize_bars(raw, ticker)
                    bars = bars[(bars.end >= session.open) & (bars.end <= received)]
                    for row in bars.to_dict("records"):
                        row["available_at"] = pd.Timestamp(received)
                        self.keep_bar(ticker, row, session.cutoff)
                        self.record_market({"ev": "AM", "sym": ticker, "origin": "massive_rest",
                            "e": int(row["end"].timestamp()*1000), "o": row["open"], "h": row["high"],
                            "l": row["low"], "c": row["close"], "v": row["volume"], "vw": row["vwap"],
                            "received_at": received.isoformat()})
                for offset in range(0, len(tickers), 4):
                    await asyncio.gather(*(fetch(ticker) for ticker in tickers[offset:offset+4]))
                self.backfill_done = session.day
                self.worker_recovered("backfill")
            await asyncio.sleep(30)

    async def consume(self):
        while True:
            event = await self.queue.get()
            try:
                self.ingest(event)
                self.last_consumed = utcnow()
                self.worker_recovered("consumer")
            finally:
                self.queue.task_done()

    def ingest(self, event):
        kind = event.get("ev")
        ticker = event.get("sym") or event.get("T")
        if not ticker or (ticker not in self.universe and ticker not in self.monitored and ticker not in {"SPY", "QQQ", "IWM"}):
            return
        if kind == "AM":
            if event.get("origin") != "massive_rest":
                recent = self.stream_bars.setdefault(ticker, deque(maxlen=5))
                if not any(previous["e"] == event["e"] for previous in recent):
                    recent.append(event)
            row = {"ticker": ticker, "end": pd.Timestamp(timestamp_ms(event["e"]), unit="ms", tz="UTC"),
                   "available_at": pd.Timestamp(event["received_at"]), "open": event["o"], "high": event["h"],
                   "low": event["l"], "close": event["c"], "volume": event["v"], "vwap": event.get("vw", event["c"])}
            event_session = self.calendar.session(row["end"].tz_convert(NY).date())
            if event_session:
                self.keep_bar(ticker, row, event_session.cutoff)
        elif kind == "Q":
            previous = self.quotes.get(ticker)
            if previous is None or int(event["t"]) > int(previous["t"]):
                self.quotes[ticker] = event
        elif kind == "T":
            previous = self.trades.get(ticker)
            if previous is None or timestamp_ms(event["t"]) > timestamp_ms(previous["t"]):
                self.trades[ticker] = event
        elif kind == "LULD":
            previous = self.luld.get(ticker)
            if previous is None or timestamp_ms(event["t"]) > timestamp_ms(previous["t"]):
                self.luld[ticker] = event
        session = self.calendar.session(pd.Timestamp(event["received_at"]).tz_convert(NY).date())
        received = pd.Timestamp(event["received_at"])
        if self.mode == "LIVE" and session and session.open <= received <= session.close:
            if kind == "AM" or received >= session.close - timedelta(minutes=30):
                self.record_market(event)

    def record_market(self, event):
        self.record_buffer.append(event)
        if len(self.record_buffer) >= 1000:
            self.flush_recorder()
            self.worker_recovered("recorder")

    def flush_recorder(self):
        if self.record_buffer:
            self.store.events("raw_market", self.record_buffer)
            self.record_buffer.clear()

    async def recorder_worker(self):
        while True:
            self.flush_recorder()
            await asyncio.sleep(1)

    async def retention_worker(self):
        while True:
            before = (utcnow()-timedelta(days=self.settings.raw_retention_days)).isoformat()
            while self.store.prune_raw(before):
                await asyncio.sleep(.1)
            self.worker_recovered("retention")
            await asyncio.sleep(3600)

    async def forward_worker(self):
        while True:
            for position in self.store.shadow_positions():
                try:
                    outcome = await resolve_shadow(self.provider, position, self.settings)
                    if outcome is not None:
                        self.store.finish_shadow(position["session"], outcome)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.status["forward_error"] = type(exc).__name__
            completed = self.store.shadow_positions(completed=True)
            for position in completed:
                path = self.settings.data_dir / "results" / f"{position['session']}.json"
                if not path.exists():
                    write_result(path.parent, position, position["outcome"])
            self.status["forward"] = forward_summary(completed)
            reasons = performance_pause(self.status["forward"], self.settings.forward_pause_drawdown)
            last_outcome = max((row["session"] for row in completed), default=None)
            acknowledged = self.store.get_state("pause_acknowledged_through")
            if reasons and last_outcome != acknowledged and not self.store.get_state("signal_pause"):
                pause = {"reasons": reasons, "at": utcnow().isoformat(), "automatic": True}
                self.store.set_state("signal_pause", pause)
                self.store.event("signal_pause", pause)
            self.status["pause"] = self.store.get_state("signal_pause")
            self.worker_recovered("forward")
            await asyncio.sleep(60)

    async def position_monitor_worker(self):
        while True:
            now = utcnow()
            monitoring = []
            self.monitored = set()
            for position in self.store.shadow_positions():
                signal = position["signal"]
                ticker = signal["winner"]
                self.monitored.add(ticker)
                quote = self.quotes.get(ticker, {})
                age = now.timestamp()-timestamp_ms(quote["t"])/1000 if quote else None
                current = age is not None and 0 <= age <= self.settings.max_quote_age
                risks = []
                if not current:
                    risks.append("CURRENT_QUOTE_UNAVAILABLE")
                if ticker in self.earnings_tickers:
                    risks.append("EARNINGS_CALENDAR_EVENT")
                if 17 in self.luld.get(ticker, {}).get("i", []):
                    risks.append("LAST_OBSERVED_LULD_HALT")
                monitoring.append({"session": position["session"], "ticker": ticker,
                                   "bid": quote.get("bp") if current else None,
                                   "quote_age": age, "risks": risks, "exit_start": signal.get("exit_start"),
                                   "exit_end": signal.get("exit_end"), "scope": "Monitoring only; original forecast unchanged"})
            self.status["positions"] = monitoring
            shortlist = set(self.ranked.head(150).ticker) if not self.ranked.empty else set()
            await self.provider.shortlist(sorted(shortlist | self.monitored))
            self.worker_recovered("position_monitor")
            await asyncio.sleep(10)

    def keep_bar(self, ticker, row, cutoff):
        """Preserve the last version known at cutoff and the latest later correction."""
        bars = self.bars.setdefault(ticker, {})
        key = row["end"]
        versions = bars.setdefault(key, [])
        partition = row["available_at"] <= cutoff
        matching = [v for v in versions if (v["available_at"] <= cutoff) == partition]
        if matching and max(v["available_at"] for v in matching) > row["available_at"]:
            return
        versions[:] = [v for v in versions if (v["available_at"] <= cutoff) != partition] + [row]
        if len(bars) > 500:
            del bars[min(bars)]

    async def ranking_worker(self):
        while True:
            await self.rank_once()
            self.worker_recovered("ranker")
            await asyncio.sleep(5)

    async def rank_once(self, now=None):
        now = now or utcnow()
        session = self.calendar.session(now.astimezone(NY).date())
        self.status.update(updated_at=now.isoformat(), provider=self.provider.health.copy(), queue_size=self.queue.qsize(),
                           next_signal=self.calendar.upcoming(now).signal.isoformat())
        self.status["telegram"] = self.telegram.health
        if not session or not session.open <= now < session.close:
            self.status["market"] = "CLOSED"
            return
        self.status["market"] = "OPEN"
        cutoff = min(pd.Timestamp(now) - pd.Timedelta(microseconds=1), pd.Timestamp(session.cutoff))
        context_key = cutoff.floor("min")
        if self.history is not None and self.history_day == session.day and self.context_minute != context_key:
            actions = await asyncio.to_thread(dated_records, self.settings.data_dir / "context" / "splits.json", cutoff)
            self.daily, self.profiles = await asyncio.to_thread(self.history.inputs, session, cutoff, actions)
            historical_features = await asyncio.to_thread(daily_features, self.daily, session.open-pd.Timedelta(microseconds=1))
            if not historical_features.empty:
                liquid = historical_features[historical_features.median_dollar_volume >= self.settings.min_dollar_volume]
                self.eligible = set(liquid.ticker) & set(self.universe)
            else:
                self.eligible = set()
            sectors = await asyncio.to_thread(dated_records, self.settings.data_dir / "context" / "sectors.json", cutoff)
            self.sectors = {row["ticker"]: row["sector"] for row in sectors}
            self.context_minute = context_key
        window = session.signal <= now <= session.signal + timedelta(seconds=self.settings.signal_grace_seconds)
        failures = list(self.status["failures"])
        if self.history_day != session.day or self.daily.empty:
            failures.append("HISTORICAL_CONTEXT_UNAVAILABLE")
        history_coverage = len(set(self.daily.ticker) & set(self.universe)) / len(self.universe) if self.universe else 0
        if history_coverage < self.settings.min_coverage:
            failures.append("REFERENCE_HISTORY_COVERAGE_INCOMPLETE")
        if not self.last_consumed or (now - self.last_consumed).total_seconds() > 60:
            failures.append("CONSUMER_STALE")
        if self.queue.qsize() >= self.settings.queue_size * .8:
            failures.append("MARKET_QUEUE_BACKLOG")
        if self.provider.health["state"] != "HEALTHY":
            failures.append("PROVIDER_UNHEALTHY")
        if not self.last_news_success or (now - self.last_news_success).total_seconds() > 180:
            failures.append("NEWS_UNAVAILABLE_OR_STALE")
        if not self.market_status_received or (now-self.market_status_received).total_seconds() > 60:
            failures.append("MARKET_STATUS_STALE")
        elif self.market_status.get("market") != "open":
            failures.append("PROVIDER_MARKET_NOT_OPEN")
        if not self.clock_evidence["valid"]:
            failures.append("CLOCK_UNVERIFIED")
        if not self.earnings_received or (now-self.earnings_received).total_seconds() > 180:
            failures.append("EARNINGS_CALENDAR_UNAVAILABLE")
        self.status["clock"] = self.clock_evidence
        feed = feed_evidence(self.provider.health, self.stream_bars, self.quotes, self.eligible, now, self.settings)
        self.status["feed_evidence"] = feed
        self.status["pipeline_failures"] = failures
        context = {"mode": self.mode, "entitlement": feed["entitlement"],
                   "model_production": self.model is not None, "coverage": 0,
                   "paused": bool(self.store.get_state("signal_pause")),
                   "signal_window": window, "failures": failures}
        rows = [row for bars in self.bars.values() for versions in bars.values() for row in versions]
        if not rows:
            self.record_decision(pd.DataFrame(), context, session, cutoff)
            return
        features = await asyncio.to_thread(build_features, pd.DataFrame(rows), self.daily, self.profiles,
                                          cutoff, session.open, self.sectors, self.news)
        if features.empty:
            self.record_decision(pd.DataFrame(), context, session, cutoff)
            return
        # Presence of one bar is not sufficient feature coverage.
        required = ["return_30m", "relative_30m", "median_dollar_volume", "rvol", "sector_relative"]
        usable = features[features[required].notna().all(axis=1)]
        covered = len(set(usable.ticker) & self.eligible)
        coverage = covered / len(self.eligible) if self.eligible else 0
        self.status["eligible"] = len(self.eligible)
        self.status["coverage"] = coverage
        context["coverage"] = coverage
        if self.model is None:
            self.status["leaderboard"] = json.loads(features.sort_values("return_30m", ascending=False).head(20).to_json(orient="records", date_format="iso"))
            self.status["leaderboard_label"] = "OBSERVED MOMENTUM — NOT MODEL RANKING"
            self.record_decision(pd.DataFrame(), context, session, cutoff)
            return
        predictions = await asyncio.to_thread(self.model.predict, features)
        risk = await asyncio.to_thread(dated_records, self.settings.data_dir / "context" / "risk.json", now)
        if self.earnings_received and 0 <= (now-self.earnings_received).total_seconds() <= 180:
            for ticker in self.eligible & self.earnings_tickers:
                # Absence from an earnings calendar says nothing about FDA/merger/other binary events.
                risk.append({"ticker": ticker, "binary_event": True,
                             "available_at": self.earnings_received.isoformat(), "source": "massive_benzinga_earnings"})
        enriched = enrich_candidates(predictions[predictions.ticker.isin(self.eligible)], self.quotes,
                                     self.luld, risk, now, trades=self.trades)
        self.ranked = rank_predictions(enriched)
        if self.mode == "LIVE":
            await self.provider.shortlist(sorted(set(self.ranked.head(150).ticker) | self.monitored))
        self.status["leaderboard"] = json.loads(self.ranked.head(20).to_json(orient="records", date_format="iso"))
        self.status["leaderboard_label"] = "MODEL RANKING"
        self.record_decision(self.ranked, context, session, cutoff)

    def record_decision(self, ranked, context, session, cutoff):
        decision = decide(ranked, context, self.settings)
        self.status["decision"] = decision["decision"]
        self.status["decision_reasons"] = decision["reasons"]
        if context["signal_window"]:
            payload = decision | {"session": str(session.day), "cutoff": cutoff.isoformat(),
                                  "exit_start": (session.next_close-timedelta(minutes=10)).isoformat(),
                                  "exit_end": (session.next_close-timedelta(minutes=2)).isoformat(),
                                  "model": self.model.metadata.get("model_id") if self.model else None, "context": context,
                                  "ranking": self.status["leaderboard"]}
            alert = signal_text(payload) if self.mode == "LIVE" else None
            if self.store.signal(session.day, self.mode, payload, alert=alert, expires=session.close.isoformat()):
                self.store.event("signal_recorded", payload)

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.flush_recorder()
        await self.provider.close()
        await self.telegram.close()
        self.store.close()
