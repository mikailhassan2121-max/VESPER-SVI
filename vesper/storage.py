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
        CREATE TRIGGER IF NOT EXISTS immutable_signals_update BEFORE UPDATE ON signals
          BEGIN SELECT RAISE(ABORT, 'Signals are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_signals_delete BEFORE DELETE ON signals
          BEGIN SELECT RAISE(ABORT, 'Signals are immutable'); END;
        """)

    def signal(self, session, mode, payload):
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO signals VALUES(?,?,?,?)",
                                     (str(session), mode, utcnow().isoformat(), json.dumps(payload, allow_nan=False)))
        return cursor.rowcount == 1

    def event(self, kind, payload):
        with self.db:
            self.db.execute("INSERT INTO events(created,kind,payload) VALUES(?,?,?)",
                            (utcnow().isoformat(), kind, json.dumps(payload, allow_nan=False)))

    def recent(self, limit=20):
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT payload FROM signals ORDER BY created DESC LIMIT ?", (limit,))]

    def close(self):
        self.db.close()
