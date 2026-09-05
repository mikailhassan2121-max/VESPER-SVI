from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import exchange_calendars as xcals

NY = ZoneInfo("America/New_York")


def utcnow():
    return datetime.now(UTC)


@dataclass(frozen=True)
class Session:
    day: date
    open: datetime
    close: datetime
    next_day: date
    next_open: datetime
    next_close: datetime

    @property
    def signal(self):
        return self.close - timedelta(minutes=10)

    @property
    def cutoff(self):
        return self.signal - timedelta(microseconds=1)


class Calendar:
    def __init__(self):
        self.exchange = xcals.get_calendar("XNYS", start="2000-01-01", end="2035-12-31")

    def session(self, day: date) -> Session | None:
        label = day.isoformat()
        if not self.exchange.is_session(label):
            return None
        nxt = self.exchange.next_session(label)
        return Session(day, self.exchange.session_open(label).to_pydatetime(),
                       self.exchange.session_close(label).to_pydatetime(), nxt.date(),
                       self.exchange.session_open(nxt).to_pydatetime(),
                       self.exchange.session_close(nxt).to_pydatetime())

    def upcoming(self, now: datetime) -> Session:
        if now.tzinfo is None:
            raise ValueError("Timezone required")
        day = now.astimezone(NY).date()
        for _ in range(15):
            session = self.session(day)
            if session and now < session.signal:
                return session
            day += timedelta(days=1)
        raise RuntimeError("Calendar has no upcoming session")
