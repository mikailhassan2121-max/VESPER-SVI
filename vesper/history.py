"""Resumable real-data acquisition; raw responses retain retrieval provenance."""
import asyncio
import json
from datetime import date, timedelta

from vesper.calendar import Calendar, utcnow
from vesper.universe import reference_universe


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
    temp.replace(path)


async def download(provider, directory, start: date, end: date):
    if end < start:
        raise ValueError("End precedes start")
    calendar = Calendar()
    day = start
    semaphore = asyncio.Semaphore(4)
    while day <= end:
        session = calendar.session(day)
        if not session:
            day += timedelta(days=1)
            continue
        folder = directory / "historical" / str(day)
        references_path = folder / "references.json"
        if references_path.exists():
            references = json.loads(references_path.read_text(encoding="utf-8"))["records"]
        else:
            references = await provider.references(day)
            atomic_json(references_path, {"as_of": str(day), "retrieved_at": utcnow().isoformat(),
                                         "source": "massive", "records": references})
        universe, rejected = reference_universe(references)
        atomic_json(folder / "universe.json", {"as_of": str(day), "eligible": list(universe), "rejected": rejected})

        async def ticker_data(ticker, folder=folder, day=day, session=session):
            # Encode ticker as a filename, avoiding Windows reserved names and path characters.
            import hashlib
            filename = hashlib.sha256(ticker.encode()).hexdigest()[:24] + ".json"
            path = folder / "minutes" / filename
            if path.exists():
                return
            async with semaphore:
                bars = await provider.bars(ticker, day, session.next_day)
                actions = await provider.actions(ticker)
                atomic_json(path, {"ticker": ticker, "as_of": str(day), "source": "massive",
                                   "retrieved_at": utcnow().isoformat(), "adjusted": False,
                                   "bars": bars, "actions": actions,
                                   "outcome_status": "AVAILABLE" if bars else "UNRESOLVED_NO_BARS"})

        # Bound both concurrent HTTP calls and the number of pending coroutine objects.
        tickers = sorted(set(universe) | {"SPY", "QQQ", "IWM"})
        for offset in range(0, len(tickers), 40):
            await asyncio.gather(*(ticker_data(ticker) for ticker in tickers[offset:offset + 40]))
        atomic_json(folder / "complete.json", {"tickers": len(tickers), "finished_at": utcnow().isoformat()})
        print(f"{day}: downloaded {len(tickers)} securities", flush=True)
        day += timedelta(days=1)
