from analysis.portfolio_analyzer import PortfolioAnalyzer
from schemas import AccountSnapshot, Position


def test_portfolio_analyzer_scores_and_sector_concentration():
    snapshot = AccountSnapshot(
        cash=1000.0,
        total_assets=11000.0,
        positions=[
            Position(
                symbol="MSFT",
                name="Microsoft",
                quantity=10,
                cost_price=300.0,
                market_price=350.0,
                market_value=3500.0,
                unrealized_pl=500.0,
                unrealized_pl_pct=16.67,
                sector="Cloud Computing",
            ),
            Position(
                symbol="NVDA",
                name="NVIDIA",
                quantity=10,
                cost_price=600.0,
                market_price=650.0,
                market_value=6500.0,
                unrealized_pl=500.0,
                unrealized_pl_pct=8.33,
                sector="Semiconductors",
            ),
        ],
    )

    result = PortfolioAnalyzer().analyze(snapshot)

    assert result.account_score > 0
    assert result.position_score > 0
    assert result.sector_concentration_score > 0
    assert result.risk_score > 0
    assert result.sector_weights["Semiconductors"] == 0.65
