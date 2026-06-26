from pathlib import Path

from data.macro_data import MacroDataClient
from llm.event_report_client import merge_macro_and_event_reports
from macro_market_intelligence_engine import MacroMarketIntelligenceEngine, default_registry


def test_macro_data_client_builds_snapshot_from_market_proxies(monkeypatch):
    values = {
        "^TNX": (4.5, 4.4),
        "DX-Y.NYB": (106.0, 105.5),
        "^VIX": (24.0, 20.0),
        "QQQ": (500.0, 495.0),
        "SPY": (600.0, 600.0),
        "IWM": (200.0, 202.0),
    }

    def fake_fetch(self, symbol):
        return values.get(symbol)

    monkeypatch.setattr(MacroDataClient, "_fetch_yahoo_previous_pair", fake_fetch)

    snapshot = MacroDataClient().get_snapshot()

    names = {item.name for item in snapshot.indicators}
    assert {"10Y", "DXY", "VIX", "NASDAQ_vs_SPX", "Russell_vs_SPX"} <= names
    assert snapshot.metadata["source"] == "yahoo-chart"


def test_merged_report_places_macro_regime_before_event_radar():
    macro_report = MacroMarketIntelligenceEngine(default_registry()).analyze(
        MacroDataClient.neutral_snapshot(as_of="2026-06-26")
    )
    event_report = "# 美股科技成长事件雷达\n\n## 今日结论\n\n事件内容"

    merged = merge_macro_and_event_reports(macro_report, event_report)

    assert merged.startswith("# 开盘前市场资金状态与科技事件雷达")
    assert "## Macro Market Intelligence" in merged
    assert "Market Regime" in merged
    assert "# 美股科技成长事件雷达" in merged
