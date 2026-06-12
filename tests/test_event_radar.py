from schemas import NewsItem
from analysis.event_analyzer import EventAnalyzer
from data.event_radar import EventRadarFetcher


def test_event_analyzer_prioritizes_ai_and_ipo_events():
    news = [
        NewsItem(
            title="CoreWeave announces new Nvidia AI data center partnership",
            symbols=["CRWV", "NVDA"],
            categories=["AI算力"],
        ),
        NewsItem(
            title="New software company files for IPO on Nasdaq",
            symbols=[],
            categories=["IPO"],
        ),
        NewsItem(title="Minor market commentary with no company catalyst"),
    ]

    events, candidates = EventAnalyzer(candidate_universe=["NVDA", "CRWV"]).analyze(news)

    assert events[0].category == "AI算力"
    assert events[0].importance_score >= 80
    assert any(event.category == "IPO" for event in events)
    assert candidates[0].symbol in {"NVDA", "CRWV"}
    assert candidates[0].status in {"重点跟踪", "跟踪候选"}


def test_event_radar_fetcher_parses_google_rss_items():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
  <item>
    <title>Nvidia supplier rallies on AI data center demand</title>
    <link>https://example.com/a</link>
    <pubDate>Thu, 11 Jun 2026 09:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""
    fetcher = EventRadarFetcher(timeout_seconds=1)

    items = fetcher._parse_rss(xml, symbols=["NVDA"], categories=["AI算力"], source="test")

    assert len(items) == 1
    assert items[0].symbols == ["NVDA"]
    assert items[0].categories == ["AI算力"]
    assert items[0].url == "https://example.com/a"


def test_event_radar_fetcher_does_not_attach_symbol_to_unrelated_title():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
  <item>
    <title>Amazon expands AI cloud partnership with chip supplier</title>
    <link>https://example.com/a</link>
    <pubDate>Thu, 11 Jun 2026 09:00:00 GMT</pubDate>
  </item>
</channel></rss>
"""
    fetcher = EventRadarFetcher(timeout_seconds=1)

    items = fetcher._parse_rss(xml, symbols=["MSFT"], categories=[], source="test")

    assert items == []
