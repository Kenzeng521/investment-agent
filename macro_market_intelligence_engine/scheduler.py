from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


class MacroMarketScheduler:
    def __init__(self, timezone: str = "America/New_York", run_hours: list[int] | None = None):
        self.timezone = ZoneInfo(timezone)
        self.run_hours = run_hours or [9]

    def should_run(self, now: datetime | None = None) -> bool:
        current = now.astimezone(self.timezone) if now else datetime.now(self.timezone)
        return current.weekday() < 5 and current.hour in self.run_hours and current.minute == 0
