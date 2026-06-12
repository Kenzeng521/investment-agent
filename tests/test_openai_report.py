from llm.openai_client import LocalReportRenderer
from schemas import (
    AccountSnapshot,
    PortfolioAnalysis,
    Position,
    PositionRisk,
    SectorScore,
)


def test_local_report_renderer_outputs_required_markdown_sections():
    snapshot = AccountSnapshot(
        cash=5000.0,
        total_assets=15000.0,
        positions=[
            Position(
                symbol="AAPL",
                name="Apple",
                quantity=10,
                cost_price=150.0,
                market_price=160.0,
                market_value=1600.0,
                unrealized_pl=100.0,
                unrealized_pl_pct=6.67,
                sector="Emerging Tech",
            )
        ],
    )
    portfolio = PortfolioAnalysis(
        account_score=82,
        position_score=80,
        sector_concentration_score=78,
        risk_score=75,
        sector_weights={"Emerging Tech": 0.11},
        summary="组合整体健康。",
    )
    risks = [
        PositionRisk(
            symbol="AAPL",
            current_price=160.0,
            cost_price=150.0,
            pnl_pct=6.67,
            stop_loss=144.0,
            take_profit_1=176.0,
            take_profit_2=192.0,
            risk_level="MEDIUM",
            position_risk="NORMAL",
        )
    ]
    sectors = [
        SectorScore(
            name="云计算",
            heat_score=78,
            capital_flow_score=70,
            growth_score=82,
            total_score=77,
            rationale="需求稳定。",
        )
    ]

    report = LocalReportRenderer().render(snapshot, portfolio, risks, sectors)

    assert "# 开盘前投资决策" in report
    assert "## 账户健康度" in report
    assert "## 当前持仓" in report
    assert "## 行业分析" in report
    assert "## 今日执行计划" in report
    assert "无需操作" in report
