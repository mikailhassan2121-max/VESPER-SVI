"""Replay actual received market events; never subscribe, alert, or write LIVE signals."""
import json
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from vesper.calendar import Calendar
from vesper.context import load_history
from vesper.modeling import Ensemble
from vesper.runtime import Runtime
from vesper.universe import reference_universe


def export_recording(database, session_day, output):
    session = Calendar().session(session_day)
    if not session:
        raise ValueError("Not a market session")
    database = Path(database).resolve()
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    count = 0
    try:
        with Path(output).open("x", encoding="utf-8") as handle:
            for (payload,) in connection.execute("SELECT payload FROM events WHERE kind='raw_market' ORDER BY json_extract(payload, '$.received_at'), id"):
                event = json.loads(payload)
                received = pd.Timestamp(event["received_at"])
                if session.open <= received <= session.close:
                    handle.write(json.dumps({"source": "massive", "event": event}) + "\n")
                    count += 1
    finally:
        connection.close()
    return {"recorded_events": count, "output": str(output)}


async def replay(settings, recording, session_day: date, output, model=None, interval=60):
    if interval < 1:
        raise ValueError("Replay interval must be positive")
    session = Calendar().session(session_day)
    if session is None:
        raise ValueError("Not a market session")
    runtime = Runtime(settings, mode="REPLAY")
    snapshots = 0
    try:
        reference_path = settings.data_dir / "historical" / str(session_day) / "references.json"
        records = json.loads(reference_path.read_text(encoding="utf-8"))["records"]
        runtime.universe, _ = reference_universe(records)
        runtime.status["universe"] = len(runtime.universe)
        runtime.history = load_history(settings.data_dir, session_day)
        runtime.history_day = session_day
        if model:
            runtime.model = Ensemble.load(model)
        prior, last_rank = None, None
        with Path(recording).open(encoding="utf-8") as reader, Path(output).open("x", encoding="utf-8") as writer:
            for line in reader:
                envelope = json.loads(line)
                if envelope.get("source") != "massive":
                    raise ValueError("Replay requires recorded Massive events")
                event = envelope["event"]
                received = pd.Timestamp(event["received_at"])
                if received.tzinfo is None or not session.open <= received <= session.close:
                    raise ValueError("Recording event outside requested session")
                if prior is not None and received < prior:
                    raise ValueError("Recording receipt timestamps are out of order")
                prior = received
                runtime.ingest(event)
                runtime.last_consumed = received
                if last_rank is None or (received-last_rank).total_seconds() >= interval:
                    await runtime.rank_once(received)
                    writer.write(json.dumps(runtime.status, allow_nan=False) + "\n")
                    snapshots += 1
                    last_rank = received
        return {"mode": "REPLAY", "snapshots": snapshots, "actionable": False, "output": str(output)}
    finally:
        await runtime.close()
