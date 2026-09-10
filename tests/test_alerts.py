import asyncio
import sqlite3
from datetime import timedelta

import httpx
import pytest

from vesper.calendar import utcnow
from vesper.config import Settings
from vesper.storage import Store
from vesper.telegram import Telegram


def test_signal_outbox_and_shadow_are_atomic_and_deduplicated(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    payload = {"decision": "BUY", "winner": "TEST", "entry": 10, "max_entry": 11}
    expires = (utcnow()+timedelta(minutes=5)).isoformat()
    assert store.signal("2026-09-04", "LIVE", payload, "BUY TEST", expires)
    assert not store.signal("2026-09-04", "LIVE", payload, "BUY TEST", expires)
    assert len(store.shadow_positions()) == 1
    assert store.db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE outbox SET text='changed'")
    store.db.rollback()
    assert store.finish_shadow("2026-09-04", {"return": .01})
    assert not store.finish_shadow("2026-09-04", {"return": .5})
    store.close()


def test_crash_during_delivery_is_unknown_not_retried(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.queue_alert("test", "text", (utcnow()+timedelta(minutes=5)).isoformat())
    store.alert_state("test", "SENDING")
    store.recover_alerts()
    assert store.pending_alert(utcnow().isoformat()) is None
    assert store.db.execute("SELECT status FROM outbox").fetchone()[0] == "UNKNOWN"
    store.close()


@pytest.mark.parametrize("timeout", [False, True])
async def test_telegram_delivery_acknowledgement_and_timeout(tmp_path, timeout):
    settings = Settings(TELEGRAM_BOT_TOKEN="fixture-token", TELEGRAM_CHAT_ID="123")
    store = Store(tmp_path / "db.sqlite")
    bot = Telegram(settings, store, {})
    await bot.http.aclose()
    called = asyncio.Event()
    def handler(request):
        called.set()
        if timeout:
            raise httpx.ReadTimeout("test timeout")
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})
    bot.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    store.queue_alert("test", "fixture", (utcnow()+timedelta(minutes=5)).isoformat())
    task = asyncio.create_task(bot.delivery())
    try:
        await asyncio.wait_for(called.wait(), timeout=3)
        await asyncio.sleep(0)
        assert store.db.execute("SELECT status FROM outbox").fetchone()[0] == ("UNKNOWN" if timeout else "SENT")
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await bot.close()
        store.close()
