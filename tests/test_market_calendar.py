from datetime import date, datetime
from zoneinfo import ZoneInfo

from scheduler.market_calendar import MarketCalendar


def test_premarket_run_window_handles_dst_utc_trigger():
    calendar = MarketCalendar("America/New_York")
    now = datetime(2026, 7, 1, 13, 0, tzinfo=ZoneInfo("UTC"))

    assert calendar.is_premarket_run_window(now, minutes_before_open=30)


def test_premarket_run_window_handles_standard_time_utc_trigger():
    calendar = MarketCalendar("America/New_York")
    now = datetime(2026, 1, 5, 14, 0, tzinfo=ZoneInfo("UTC"))

    assert calendar.is_premarket_run_window(now, minutes_before_open=30)


def test_premarket_run_window_rejects_duplicate_utc_trigger():
    calendar = MarketCalendar("America/New_York")
    now = datetime(2026, 7, 1, 14, 0, tzinfo=ZoneInfo("UTC"))

    assert not calendar.is_premarket_run_window(now, minutes_before_open=30)


def test_market_calendar_recognizes_observed_us_market_holidays():
    calendar = MarketCalendar("America/New_York")

    assert not calendar.is_trading_day(date(2026, 1, 1))
    assert not calendar.is_trading_day(date(2026, 6, 19))
    assert not calendar.is_trading_day(date(2027, 12, 24))
    assert calendar.is_trading_day(date(2027, 12, 23))
