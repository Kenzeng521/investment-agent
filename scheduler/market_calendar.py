from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


class MarketCalendar:
    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = ZoneInfo(timezone)

    def is_trading_day(self, day: date | None = None) -> bool:
        day = day or datetime.now(self.timezone).date()
        return day.weekday() < 5 and day not in us_market_holidays(day.year)

    def next_premarket_run_time(self, now: datetime | None = None, minutes_before_open: int = 30) -> datetime:
        current = now.astimezone(self.timezone) if now else datetime.now(self.timezone)
        candidate_day = current.date()
        market_open = time(9, 30)
        while True:
            run_dt = datetime.combine(candidate_day, market_open, self.timezone) - timedelta(minutes=minutes_before_open)
            if self.is_trading_day(candidate_day) and run_dt > current:
                return run_dt
            candidate_day += timedelta(days=1)

    def is_premarket_run_window(
        self,
        now: datetime | None = None,
        minutes_before_open: int = 30,
        tolerance_minutes: int = 10,
    ) -> bool:
        current = now.astimezone(self.timezone) if now else datetime.now(self.timezone)
        if not self.is_trading_day(current.date()):
            return False
        market_open = time(9, 30)
        run_dt = datetime.combine(current.date(), market_open, self.timezone) - timedelta(
            minutes=minutes_before_open
        )
        window_end = run_dt + timedelta(minutes=tolerance_minutes)
        return run_dt <= current <= window_end


def us_market_holidays(year: int) -> set[date]:
    return {
        _observed_fixed_holiday(year, 1, 1),
        _nth_weekday(year, 1, weekday=0, n=3),
        _nth_weekday(year, 2, weekday=0, n=3),
        _good_friday(year),
        _last_weekday(year, 5, weekday=0),
        _observed_fixed_holiday(year, 6, 19),
        _observed_fixed_holiday(year, 7, 4),
        _nth_weekday(year, 9, weekday=0, n=1),
        _nth_weekday(year, 11, weekday=3, n=4),
        _observed_fixed_holiday(year, 12, 25),
    }


def _observed_fixed_holiday(year: int, month: int, day: int) -> date:
    holiday = date(year, month, day)
    if holiday.weekday() == 5:
        return holiday - timedelta(days=1)
    if holiday.weekday() == 6:
        return holiday + timedelta(days=1)
    return holiday


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    current = date(year, month, 1)
    days_until_weekday = (weekday - current.weekday()) % 7
    return current + timedelta(days=days_until_weekday + (n - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    current = date(year + int(month == 12), 1 if month == 12 else month + 1, 1) - timedelta(days=1)
    while current.weekday() != weekday:
        current -= timedelta(days=1)
    return current


def _good_friday(year: int) -> date:
    # Anonymous Gregorian algorithm.
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    easter_month = (h + l - 7 * m + 114) // 31
    easter_day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, easter_month, easter_day) - timedelta(days=2)
