import json
from datetime import date

import pandas as pd

from vesper.calendar import Calendar
from vesper.config import Settings
from vesper.replay import export_recording, replay
from vesper.storage import Store


async def test_replay_uses_separate_store_and_never_connects(tmp_path, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Replay attempted a network request")
    monkeypatch.setattr("vesper.provider.Massive.get", forbidden)
    settings = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models", MASSIVE_API_KEY="")
    session = Calendar().session(date(2026, 9, 4))
    folder = settings.data_dir / "historical" / str(session.day)
    folder.mkdir(parents=True)
    reference = {"ticker": "TEST", "type": "CS", "market": "stocks", "locale": "us", "active": True,
                 "primary_exchange": "XNYS"}
    (folder / "references.json").write_text(json.dumps({"records": [reference]}))
    recording = tmp_path / "recording.jsonl"
    events = []
    for received in (session.open+pd.Timedelta(minutes=1), session.signal):
        events.append({"source": "massive", "event": {"ev": "AM", "sym": "TEST", "o": 10, "h": 11,
            "l": 9, "c": 10, "v": 100, "vw": 10, "e": int(received.timestamp()*1000)-1,
            "received_at": received.isoformat()}})
    recording.write_text("\n".join(json.dumps(e) for e in events))
    output = tmp_path / "snapshots.jsonl"
    result = await replay(settings, recording, session.day, output)
    assert result["mode"] == "REPLAY"
    assert result["actionable"] is False
    assert not (settings.data_dir / "vesper.sqlite").exists()
    store = Store(settings.data_dir / "replay.sqlite")
    try:
        assert "NON_LIVE_MODE" in store.recent()[0]["reasons"]
    finally:
        store.close()


def test_export_orders_receipt_time_even_when_writers_interleave(tmp_path):
    database = tmp_path / "live.sqlite"
    store = Store(database)
    store.events("raw_market", [{"received_at": "2026-09-04T19:45:00+00:00"},
                                {"received_at": "2026-09-04T19:44:00+00:00"}])
    store.close()
    output = tmp_path / "recording.jsonl"
    result = export_recording(database, date(2026, 9, 4), output)
    assert result["recorded_events"] == 2
    events = [json.loads(line)["event"] for line in output.read_text().splitlines()]
    assert events[0]["received_at"] < events[1]["received_at"]
