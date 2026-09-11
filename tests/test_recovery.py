import os
import subprocess
import sys
import time

from vesper.forward import forward_summary, performance_pause
from vesper.storage import Store


def test_forward_pause_and_drawdown():
    rows = [{"session": f"2026-01-{i+1:02d}", "outcome": {"return": -.01, "excess_return": -.005}} for i in range(20)]
    summary = forward_summary(rows)
    assert summary["max_drawdown"] < -.15
    assert set(performance_pause(summary)) == {"FORWARD_DRAWDOWN_LIMIT", "NEGATIVE_20_SESSION_RETURN_AND_EXCESS"}
    assert not performance_pause(forward_summary([]))


def test_retention_preserves_audit_and_signal_records(tmp_path):
    store = Store(tmp_path/'state.sqlite')
    try:
        store.event('raw_market', {'fixture': True})
        store.event('signal_recorded', {'fixture': True})
        store.signal('2026-01-02', 'REPLAY', {'decision': 'NO TRADE'})
        assert store.prune_raw('9999', batch=1) == 1
        assert store.prune_raw('9999') == 0
        assert store.db.execute('SELECT kind FROM events').fetchone()[0] == 'signal_recorded'
        assert len(store.recent()) == 1
    finally:
        store.close()


def test_forced_process_termination_recovers_committed_signal_without_resending(tmp_path):
    database = tmp_path/'crash.sqlite'
    ready = tmp_path/'ready'
    script = '''
import sys,time
from pathlib import Path
from vesper.storage import Store
s=Store(Path(sys.argv[1]))
s.signal('2026-01-02','LIVE',{'decision':'NO TRADE'},alert='UNIT FIXTURE; NEVER SENT',expires='2099-01-01')
s.alert_state('signal:2026-01-02','SENDING')
Path(sys.argv[2]).touch()
time.sleep(60)
'''
    process = subprocess.Popen([sys.executable, '-c', script, str(database), str(ready)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        deadline = time.monotonic()+10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        assert ready.exists(), 'Fixture process failed to commit its state'
        process.kill()
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stderr.close()
    store = Store(database)
    try:
        assert len(store.recent()) == 1
        assert not store.signal('2026-01-02', 'LIVE', {'decision': 'NO TRADE'})
        store.recover_alerts()
        assert store.db.execute('SELECT status FROM outbox').fetchone()[0] == 'UNKNOWN'
        assert store.pending_alert('2026-01-03') is None
        assert store.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    finally:
        store.close()
