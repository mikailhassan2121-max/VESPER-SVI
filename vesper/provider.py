"""Read-only Massive adapter. No brokerage client or execution endpoint."""
import asyncio
import json
import random
from urllib.parse import quote, urlparse

import httpx
from websockets.asyncio.client import connect

from vesper.calendar import utcnow


class ProviderError(RuntimeError):
    pass


def timestamp_ms(value):
    # Some channels document milliseconds but show nanoseconds in examples.
    value = int(value)
    if value > 10**17:
        return value / 1_000_000
    if value > 10**14:
        return value / 1000
    if value < 10**11:
        raise ValueError("Unexpected provider timestamp unit")
    return value


class Massive:
    REST = "https://api.massive.com"
    STREAM = "wss://socket.massive.com/stocks"

    def __init__(self, key):
        self.key = key
        self.http = httpx.AsyncClient(timeout=30, headers={"Authorization": f"Bearer {key}"})
        self.health = {"state": "DISCONNECTED", "entitlement": "UNAVAILABLE", "reconnects": 0,
                       "last_message": None, "messages": 0, "error": None}
        self.subscriptions = {"AM.*", "LULD.*"}
        self.socket = None
        self.subscription_lock = asyncio.Lock()

    async def close(self):
        await self.http.aclose()

    async def get(self, path, params=None):
        if not self.key:
            raise ProviderError("MASSIVE_API_KEY is not configured")
        url = path if path.startswith("https://") else self.REST + path
        if urlparse(url).netloc != "api.massive.com" or urlparse(url).scheme != "https":
            raise ProviderError("Rejected foreign pagination URL")
        for attempt in range(5):
            try:
                response = await self.http.get(url, params=params)
            except httpx.RequestError:
                if attempt == 4:
                    raise ProviderError("Provider network request failed") from None
                await asyncio.sleep(min(2 ** attempt, 8))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                await asyncio.sleep(min(2 ** attempt, 8) + random.random())
                continue
            if response.status_code != 200:
                raise ProviderError(f"Provider HTTP {response.status_code}; check subscription and credentials")
            data = response.json()
            if data.get("status") in {"ERROR", "NOT_AUTHORIZED"}:
                raise ProviderError("Provider rejected request")
            return data
        raise ProviderError("Provider retry budget exhausted")

    async def pages(self, path, params=None):
        rows, seen = [], set()
        while path:
            if path in seen:
                raise ProviderError("Pagination loop")
            seen.add(path)
            data = await self.get(path, params)
            rows.extend(data.get("results", []))
            path, params = data.get("next_url"), None
        return rows

    async def references(self, day):
        return await self.pages("/v3/reference/tickers", {"market": "stocks", "locale": "us",
                                "date": str(day), "active": "true", "limit": 1000})

    async def market_status(self):
        return await self.get("/v1/marketstatus/now")

    async def earnings(self, start, end):
        return await self.pages("/benzinga/v1/earnings", {"date.gte": str(start), "date.lte": str(end), "limit": 1000})

    async def detail(self, ticker, day):
        data = await self.get(f"/v3/reference/tickers/{quote(ticker, safe='')}", {"date": str(day)})
        return data.get("results", {})

    async def bars(self, ticker, start, end, timespan="minute"):
        return await self.pages(f"/v2/aggs/ticker/{quote(ticker, safe='')}/range/1/{timespan}/{start}/{end}",
                                {"adjusted": "false", "sort": "asc", "limit": 50000})

    async def news(self, cutoff, since):
        return await self.pages("/v2/reference/news", {"published_utc.lte": cutoff.isoformat(),
                               "published_utc.gte": since.isoformat(), "limit": 1000})

    async def actions(self, ticker):
        splits = await self.pages("/stocks/v1/splits", {"ticker": ticker, "limit": 1000})
        dividends = await self.pages("/stocks/v1/dividends", {"ticker": ticker, "limit": 1000})
        return {"splits": splits, "dividends": dividends}

    async def shortlist(self, tickers):
        desired = {"AM.*", "LULD.*"} | {f"{channel}.{ticker}" for ticker in tickers for channel in ("Q", "T")}
        async with self.subscription_lock:
            old = self.subscriptions
            self.subscriptions = desired
            if self.socket:
                for action, channels in (("unsubscribe", old - desired), ("subscribe", desired - old)):
                    if channels:
                        await self.socket.send(json.dumps({"action": action, "params": ",".join(sorted(channels))}))

    async def stream(self, queue):
        if not self.key:
            self.health.update(state="FAILED", error="MASSIVE_API_KEY is not configured")
            return
        attempt = 0
        while True:
            try:
                self.health.update(state="RECONNECTING", entitlement="UNAVAILABLE")
                async with connect(self.STREAM, ping_interval=20, ping_timeout=20, max_queue=32,
                                   open_timeout=15, max_size=8_000_000) as ws:
                    await ws.send(json.dumps({"action": "auth", "params": self.key}))
                    authenticated = False
                    while True:
                        raw = await asyncio.wait_for(ws.recv(), timeout=90)
                        received = utcnow()
                        for event in json.loads(raw):
                            if event.get("ev") == "status":
                                status = event.get("status")
                                if status == "auth_success":
                                    authenticated = True
                                    async with self.subscription_lock:
                                        self.socket = ws
                                        await ws.send(json.dumps({"action": "subscribe",
                                                                 "params": ",".join(sorted(self.subscriptions))}))
                                elif status in {"auth_failed", "error"}:
                                    raise ProviderError("Stream authentication/subscription rejected")
                                continue
                            if not authenticated:
                                raise ProviderError("Unauthenticated stream data")
                            event["received_at"] = received.isoformat()
                            await queue.put(event)
                            self.health.update(last_message=received.isoformat(), state="HEALTHY")
                            self.health["messages"] += 1
                            # Connection/authentication alone never proves entitlement.
                            ts = event.get("e") if event.get("ev") == "AM" else event.get("t")
                            if ts:
                                age = received.timestamp() - timestamp_ms(ts) / 1000
                                self.health["latency_seconds"] = age
                                if age > 600:
                                    self.health["entitlement"] = "DELAYED"
                                elif 0 <= age < 90:
                                    self.health["entitlement"] = "REALTIME_LIMITED"
                            attempt = 0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.health.update(state="DISCONNECTED", entitlement="UNAVAILABLE", error=type(exc).__name__)
                self.health["reconnects"] += 1
                attempt += 1
            finally:
                self.socket = None
            await asyncio.sleep(min(30, 2 ** min(attempt, 5)) + random.random())
