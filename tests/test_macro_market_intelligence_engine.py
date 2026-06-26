from datetime import datetime
from zoneinfo import ZoneInfo

from macro_market_intelligence_engine import (
    AssetRegistration,
    MacroIndicatorReading,
    MacroMarketIntelligenceEngine,
    MacroMarketScheduler,
    MacroSnapshot,
    default_registry,
)


def test_engine_identifies_risk_off_from_multi_variable_convergence():
    engine = MacroMarketIntelligenceEngine(default_registry())
    snapshot = MacroSnapshot(
        as_of="2026-06-26",
        indicators=[
            MacroIndicatorReading(name="10Y", value=4.5, change=0.12),
            MacroIndicatorReading(name="RealYield", value=2.1, change=0.08),
            MacroIndicatorReading(name="DXY", value=106.0, change=0.7),
            MacroIndicatorReading(name="VIX", value=24.0, change=4.0),
            MacroIndicatorReading(name="MOVE", value=120.0, change=8.0),
            MacroIndicatorReading(name="ETF_Flows", value=-4.2, change=-4.2),
            MacroIndicatorReading(name="Russell_vs_SPX", value=-1.1, change=-1.1),
        ],
    )

    report = engine.analyze(snapshot)

    assert report.market_regime.regime == "Risk-Off"
    assert "多变量共振" in report.market_regime.reason
    assert report.signal_summary.evidence_count >= 3
    assert "宏观" in report.flow_narrative
    assert "流动性" in report.flow_narrative
    assert "风险偏好" in report.flow_narrative
    assert "资金流" in report.flow_narrative
    assert "估值" in report.flow_narrative
    assert report.asset_impacts["MSFT"].symbol == "MSFT"
    assert "折现率" in report.asset_impacts["MSFT"].impact_path
    assert report.asset_impacts["ATXI"].symbol == "ATXI"
    assert "被动抛售" in report.asset_impacts["ATXI"].impact_path
    assert report.position_preference == "防御 / 现金优先 / 小盘回避"


def test_engine_identifies_repricing_when_rates_rise_but_volatility_is_stable():
    engine = MacroMarketIntelligenceEngine(default_registry())
    snapshot = MacroSnapshot(
        as_of="2026-06-26",
        indicators=[
            MacroIndicatorReading(name="10Y", value=4.45, change=0.10),
            MacroIndicatorReading(name="RealYield", value=2.05, change=0.07),
            MacroIndicatorReading(name="VIX", value=15.0, change=0.1),
            MacroIndicatorReading(name="DXY", value=104.0, change=0.1),
            MacroIndicatorReading(name="Mag7_vs_EqualWeight", value=0.9, change=0.9),
            MacroIndicatorReading(name="Russell_vs_SPX", value=-0.4, change=-0.4),
        ],
    )

    report = engine.analyze(snapshot)

    assert report.market_regime.regime == "Repricing"
    assert report.position_preference == "结构性轮动 / 降杠杆但保核心资产"
    assert "估值结构调整" in report.market_regime.reason


def test_engine_identifies_risk_on_when_liquidity_and_risk_appetite_improve():
    engine = MacroMarketIntelligenceEngine(default_registry())
    snapshot = MacroSnapshot(
        as_of="2026-06-26",
        indicators=[
            MacroIndicatorReading(name="10Y", value=4.1, change=-0.12),
            MacroIndicatorReading(name="RealYield", value=1.75, change=-0.09),
            MacroIndicatorReading(name="DXY", value=101.0, change=-0.6),
            MacroIndicatorReading(name="VIX", value=12.5, change=-2.5),
            MacroIndicatorReading(name="ETF_Flows", value=5.0, change=5.0),
            MacroIndicatorReading(name="NASDAQ_vs_SPX", value=1.0, change=1.0),
            MacroIndicatorReading(name="Russell_vs_SPX", value=0.8, change=0.8),
        ],
    )

    report = engine.analyze(snapshot)

    assert report.market_regime.regime == "Risk-On"
    assert report.position_preference == "成长 / AI / 高β偏多"
    assert "流动性扩张先压低风险偏好" not in report.asset_impacts["ATXI"].impact_path
    assert "一旦流动性收紧" in report.asset_impacts["ATXI"].impact_path


def test_engine_supports_extensible_asset_registration_and_json_text_output():
    registry = default_registry()
    registry.register_asset(
        AssetRegistration(
            symbol="NVDA",
            role="AI拥挤交易核心资产",
            sensitivities=["实际利率", "风险偏好", "ETF资金流"],
            mechanism_template=(
                "{symbol}作为{role}，在{regime}中主要通过{liquidity_phrase}影响风险偏好，"
                "再经由ETF与主题资金流改变AI拥挤交易的边际买盘，最终反映到估值弹性。"
            ),
        )
    )
    engine = MacroMarketIntelligenceEngine(registry)
    report = engine.analyze(
        MacroSnapshot(
            as_of="2026-06-26",
            indicators=[
                MacroIndicatorReading(name="10Y", value=4.1, change=-0.12),
                MacroIndicatorReading(name="VIX", value=12.5, change=-2.5),
                MacroIndicatorReading(name="ETF_Flows", value=5.0, change=5.0),
            ],
        )
    )

    payload = report.to_json_dict()
    text = report.to_wechat_text()

    assert "NVDA" in payload["asset_impact"]["assets"]
    assert "Market Regime" in text
    assert "Flow Narrative" in text
    assert "Asset Impact" in text


def test_scheduler_uses_configurable_time_window_without_sending_messages():
    scheduler = MacroMarketScheduler(timezone="Asia/Shanghai", run_hours=[21, 22])

    assert scheduler.should_run(datetime(2026, 6, 26, 21, 0, tzinfo=ZoneInfo("Asia/Shanghai")))
    assert not scheduler.should_run(datetime(2026, 6, 26, 20, 59, tzinfo=ZoneInfo("Asia/Shanghai")))
