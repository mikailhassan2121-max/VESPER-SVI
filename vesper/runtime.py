import asyncio
import json
from collections import deque
from datetime import timedelta

import pandas as pd

from vesper.calendar import NY, Calendar, utcnow
from vesper.decision import decide, rank_predictions
from vesper.features import build_features, normalize_bars
from vesper.modeling import Ensemble
from vesper.provider import Massive, timestamp_ms
from vesper.storage import Store
from vesper.universe import reference_universe


class Runtime:
    def __init__(self, settings):
        self.settings = settings
        settings.prepare()
        self.calendar = Calendar()
        self.provider = Massive(settings.massive_api_key.get_secret_value())
        self.store = Store(settings.data_dir / "vesper.sqlite")
        self.queue = asyncio.Queue(maxsize=settings.queue_size)
        self.bars, self.quotes, self.luld = {}, {}, {}
        self.tasks = []
        self.model = None
        self.universe = {}
        self.ranked = pd.DataFrame()
        self.stop_event = asyncio.Event()
        self.status = {"mode": "LIVE", "decision": "NO SIGNAL — SYSTEM INVALID", "failures": [],
                       "leaderboard": [], "production_validated": False, "universe": 0}
        self.daily = normalize_bars([], "")
        self.profiles, self.sectors = {}, {}
        self.news = None

    async def start(self):
        try:
            self.model = Ensemble.load(self.settings.model_dir / "production", production=True)
        except (OSError, ValueError, KeyError):
            self.status["failures"].append("PRODUCTION_MODEL_UNAVAILABLE")
        self.tasks = [asyncio.create_task(self.supervise("reference", self.reference_worker)),
                      asyncio.create_task(self.provider.stream(self.queue)),
                      asyncio.create_task(self.supervise("consumer", self.consume)),
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

    async def reference_worker(self):
        current_day = None
        while True:
            day = utcnow().astimezone(NY).date()
            if day != current_day:
                references = await self.provider.references(day)
                self.universe, rejected = reference_universe(references)
                self.status.update(universe=len(self.universe), rejected=rejected)
                self.store.event("universe", {"date": str(day), "tickers": list(self.universe), "rejected": rejected})
                current_day = day
            await asyncio.sleep(60)

    async def consume(self):
        while True:
            event = await self.queue.get()
            try:
                self.ingest(event)
            finally:
                self.queue.task_done()

    def ingest(self, event):
        kind = event.get("ev")
        ticker = event.get("sym") or event.get("T")
        if not ticker or (ticker not in self.universe and ticker not in {"SPY", "QQQ", "IWM"}):
            return
        if kind == "AM":
            row = {"ticker": ticker, "end": pd.Timestamp(timestamp_ms(event["e"]), unit="ms", tz="UTC"),
                   "available_at": pd.Timestamp(event["received_at"]), "open": event["o"], "high": event["h"],
                   "low": event["l"], "close": event["c"], "volume": event["v"], "vwap": event.get("vw", event["c"])}
            self.bars.setdefault(ticker, deque(maxlen=500)).append(row)
        elif kind == "Q":
            previous = self.quotes.get(ticker)
            if previous is None or int(event["t"]) > int(previous["t"]):
                self.quotes[ticker] = event
        elif kind == "LULD":
            self.luld[ticker] = event
        session = self.calendar.session(pd.Timestamp(event["received_at"]).tz_convert(NY).date())
        if session and session.close - timedelta(minutes=30) <= pd.Timestamp(event["received_at"]) <= session.close:
            self.store.event("raw_market", event)

    async def ranking_worker(self):
        while True:
            await self.rank_once()
            await asyncio.sleep(5)

    async def rank_once(self):
        now = utcnow()
        session = self.calendar.session(now.astimezone(NY).date())
        self.status.update(updated_at=now.isoformat(), provider=self.provider.health.copy(), queue_size=self.queue.qsize(),
                           next_signal=self.calendar.upcoming(now).signal.isoformat())
        if not session or not session.open <= now < session.close:
            self.status["market"] = "CLOSED"
            return
        self.status["market"] = "OPEN"
        cutoff = min(pd.Timestamp(now) - pd.Timedelta(microseconds=1), pd.Timestamp(session.cutoff))
        rows = [row for bars in self.bars.values() for row in bars]
        if not rows:
            return
        features = await asyncio.to_thread(build_features, pd.DataFrame(rows), self.daily, self.profiles,
                                          cutoff, session.open, self.sectors, self.news)
        if features.empty:
            return
        covered = len(set(features.ticker) & set(self.universe))
        coverage = covered / len(self.universe) if self.universe else 0
        self.status["coverage"] = coverage
        if self.model is None:
            self.status["leaderboard"] = json.loads(features.sort_values("return_30m", ascending=False).head(20).to_json(orient="records", date_format="iso"))
            self.status["leaderboard_label"] = "OBSERVED MOMENTUM — NOT MODEL RANKING"
            return
        predictions = await asyncio.to_thread(self.model.predict, features)
        self.ranked = rank_predictions(predictions[predictions.ticker.isin(self.universe)])
        await self.provider.shortlist(self.ranked.head(150).ticker.to_list())
        self.status["leaderboard"] = json.loads(self.ranked.head(20).to_json(orient="records", date_format="iso"))
        self.status["leaderboard_label"] = "MODEL RANKING"
        window = session.signal <= now <= session.signal + timedelta(seconds=self.settings.signal_grace_seconds)
        context = {"mode": "LIVE", "entitlement": self.provider.health["entitlement"],
                   "model_production": True, "coverage": coverage, "signal_window": window,
                   "failures": self.status["failures"]}
        decision = decide(self.ranked, context, self.settings)
        self.status["decision"] = decision["decision"]
        if window:
            payload = decision | {"session": str(session.day), "cutoff": cutoff.isoformat(),
                                  "model": self.model.metadata.get("model_id"), "context": context,
                                  "ranking": self.status["leaderboard"]}
            if self.store.signal(session.day, "LIVE", payload):
                self.store.event("signal_recorded", payload)

    async def close(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.provider.close()
        self.store.close()
