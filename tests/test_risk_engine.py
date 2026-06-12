from analysis.risk_engine import RiskEngine
from schemas import Position


def test_risk_engine_calculates_stop_and_targets_from_cost_and_price():
    position = Position(
        symbol="NVDA",
        name="NVIDIA",
        quantity=10,
        cost_price=100.0,
        market_price=120.0,
        market_value=1200.0,
        unrealized_pl=200.0,
        unrealized_pl_pct=20.0,
        sector="Semiconductors",
    )

    result = RiskEngine().analyze_position(position)

    assert result.symbol == "NVDA"
    assert result.stop_loss == 108.0
    assert result.take_profit_1 == 132.0
    assert result.take_profit_2 == 144.0
    assert result.risk_level in {"LOW", "MEDIUM", "HIGH"}


def test_auto_trading_is_disabled_by_default():
    engine = RiskEngine()

    assert engine.auto_trading_enabled is False
