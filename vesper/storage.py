import json
import sqlite3
from pathlib import Path

from vesper.calendar import utcnow


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS signals(
          session TEXT NOT NULL, mode TEXT NOT NULL, created TEXT NOT NULL,
          payload TEXT NOT NULL, PRIMARY KEY(session, mode));
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY, created TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox(
          key TEXT PRIMARY KEY, text TEXT NOT NULL, created TEXT NOT NULL, expires TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'PENDING', detail TEXT, available TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS shadow_positions(
          session TEXT PRIMARY KEY, payload TEXT NOT NULL, outcome TEXT);
        CREATE TRIGGER IF NOT EXISTS immutable_alert_text BEFORE UPDATE OF text ON outbox
          BEGIN SELECT RAISE(ABORT, 'Alert text is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_shadow BEFORE UPDATE OF payload ON shadow_positions
          BEGIN SELECT RAISE(ABORT, 'Original shadow forecast is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_outcome BEFORE UPDATE OF outcome ON shadow_positions
          WHEN OLD.outcome IS NOT NULL BEGIN SELECT RAISE(ABORT, 'Outcome already recorded'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_signals_update BEFORE UPDATE ON signals
          BEGIN SELECT RAISE(ABORT, 'Signals are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_signals_delete BEFORE DELETE ON signals
          BEGIN SELECT RAISE(ABORT, 'Signals are immutable'); END;
        """)

    def signal(self, session, mode, payload, alert=None, expires=None):
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO signals VALUES(?,?,?,?)",
                                     (str(session), mode, utcnow().isoformat(), json.dumps(payload, allow_nan=False)))
            if cursor.rowcount == 1 and mode == "LIVE":
                if payload.get("decision") == "BUY":
                    self.db.execute("INSERT INTO shadow_positions VALUES(?,?,NULL)",
                                    (str(session), json.dumps(payload, allow_nan=False)))
                if alert and expires:
                    self._queue(f"signal:{session}", alert, expires)
        return cursor.rowcount == 1

    def _queue(self, key, text, expires):
        now = utcnow().isoformat()
        self.db.execute("INSERT OR IGNORE INTO outbox(key,text,created,expires,available) VALUES(?,?,?,?,?)",
                        (key, text, now, expires, now))

    def queue_alert(self, key, text, expires):
        with self.db:
            self._queue(key, text, expires)

    def get_state(self, key, default=None):
        row = self.db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_state(self, key, value):
        with self.db:
            self.db.execute("INSERT INTO state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (key, json.dumps(value)))

    def pending_alert(self, now):
        with self.db:
            self.db.execute("UPDATE outbox SET status='EXPIRED' WHERE status='PENDING' AND expires<=?", (now,))
        return self.db.execute("SELECT key,text FROM outbox WHERE status='PENDING' AND available<=? ORDER BY created LIMIT 1", (now,)).fetchone()

    def alert_state(self, key, status, detail=None, available=None):
        with self.db:
            self.db.execute("UPDATE outbox SET status=?,detail=?,available=COALESCE(?,available) WHERE key=?",
                            (status, detail, available, key))

    def recover_alerts(self):
        # A crash after sending but before acknowledgement cannot be retried safely.
        with self.db:
            self.db.execute("UPDATE outbox SET status='UNKNOWN',detail='Process stopped during delivery' WHERE status='SENDING'")

    def shadow_positions(self, completed=False):
        rows = self.db.execute("SELECT session,payload,outcome FROM shadow_positions WHERE outcome IS " +
                               ("NOT NULL" if completed else "NULL"))
        return [{"session": r[0], "signal": json.loads(r[1]), "outcome": json.loads(r[2]) if r[2] else None} for r in rows]

    def finish_shadow(self, session, outcome):
        with self.db:
            result = self.db.execute("UPDATE shadow_positions SET outcome=? WHERE session=? AND outcome IS NULL",
                                     (json.dumps(outcome, allow_nan=False), session))
        return result.rowcount == 1

    def event(self, kind, payload):
        with self.db:
            self.db.execute("INSERT INTO events(created,kind,payload) VALUES(?,?,?)",
                            (utcnow().isoformat(), kind, json.dumps(payload, allow_nan=False)))

    def events(self, kind, payloads):
        created = utcnow().isoformat()
        with self.db:
            self.db.executemany("INSERT INTO events(created,kind,payload) VALUES(?,?,?)",
                                [(created, kind, json.dumps(payload, allow_nan=False)) for payload in payloads])

    def recent(self, limit=20):
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT payload FROM signals ORDER BY created DESC LIMIT ?", (limit,))]

    def prune_raw(self, before, batch=5000):
        # Signals, outcomes, and audit events are never subject to raw-feed retention.
        with self.db:
            result = self.db.execute("DELETE FROM events WHERE id IN (SELECT id FROM events "
                                     "WHERE kind='raw_market' AND created<? ORDER BY id LIMIT ?)", (before, batch))
        return result.rowcount

    def close(self):
        self.db.close()
