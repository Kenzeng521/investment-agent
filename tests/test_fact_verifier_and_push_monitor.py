from datetime import date

from analysis.event_analyzer import EventAnalyzer
from data.event_radar import EventRadarFetcher
from notify.push_monitor import PushMonitor
from schemas import NewsItem


def test_event_radar_parses_publisher_from_google_title():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
  <item>
    <title>Microsoft signs AI power deal - Reuters</title>
    <link>https://example.com/a</link>
  </item>
</channel></rss>
"""

    items = EventRadarFetcher(timeout_seconds=1)._parse_rss(
        xml, symbols=["MSFT"], categories=["AI算力"], source="google-news"
    )

    assert items[0].source == "Reuters"
    assert items[0].title == "Microsoft signs AI power deal"


def test_event_analyzer_adds_fact_verification_status():
    events, _ = EventAnalyzer(candidate_universe=["MSFT"]).analyze(
        [
            NewsItem(
                title="Microsoft signs AI power deal",
                source="Reuters",
                symbols=["MSFT"],
                categories=["AI算力"],
            ),
            NewsItem(title="Rumor says unknown AI stock will explode", source="anonymous blog"),
        ]
    )

    by_title = {event.title: event for event in events}
    assert by_title["Microsoft signs AI power deal"].verification_status == "较可信"
    assert by_title["Rumor says unknown AI stock will explode"].verification_status == "低可信"


def test_push_monitor_tracks_success_and_prevents_duplicate(tmp_path):
    monitor = PushMonitor(tmp_path / "push_state.json")

    assert not monitor.was_successful("event_radar", date(2026, 6, 26))
    monitor.record_success("event_radar", date(2026, 6, 26), report_path="reports/latest.md")

    assert monitor.was_successful("event_radar", date(2026, 6, 26))
    state = monitor.load()
    assert state["event_radar"]["2026-06-26"]["status"] == "success"
