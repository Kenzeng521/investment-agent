from __future__ import annotations

from dataclasses import dataclass, field

from .models import AssetRegistration, IndicatorRegistration


@dataclass
class MacroMarketRegistry:
    indicators: dict[str, IndicatorRegistration] = field(default_factory=dict)
    assets: dict[str, AssetRegistration] = field(default_factory=dict)

    def register_indicator(self, indicator: IndicatorRegistration) -> None:
        self.indicators[indicator.name.upper()] = indicator

    def get_indicator(self, name: str) -> IndicatorRegistration | None:
        return self.indicators.get(name.upper())

    def register_asset(self, asset: AssetRegistration) -> None:
        self.assets[asset.symbol.upper()] = asset

    def get_asset(self, symbol: str) -> AssetRegistration | None:
        return self.assets.get(symbol.upper())


def default_registry() -> MacroMarketRegistry:
    registry = MacroMarketRegistry()
    for indicator in [
        IndicatorRegistration(
            name="10Y",
            category="rates",
            higher_change_direction="liquidity_tightening",
            lower_change_direction="liquidity_expansion",
            threshold=0.02,
            label="10年期美债收益率",
        ),
        IndicatorRegistration(
            name="2Y",
            category="rates",
            higher_change_direction="liquidity_tightening",
            lower_change_direction="liquidity_expansion",
            threshold=0.02,
            label="2年期美债收益率",
        ),
        IndicatorRegistration(
            name="RealYield",
            category="rates",
            higher_change_direction="valuation_pressure",
            lower_change_direction="valuation_support",
            threshold=0.02,
            label="实际利率",
        ),
        IndicatorRegistration(
            name="DXY",
            category="dollar",
            higher_change_direction="liquidity_tightening",
            lower_change_direction="liquidity_expansion",
            threshold=0.1,
            label="美元指数",
        ),
        IndicatorRegistration(
            name="VIX",
            category="volatility",
            higher_change_direction="risk_appetite_down",
            lower_change_direction="risk_appetite_up",
            threshold=0.5,
            label="VIX",
        ),
        IndicatorRegistration(
            name="MOVE",
            category="volatility",
            higher_change_direction="risk_appetite_down",
            lower_change_direction="risk_appetite_up",
            threshold=1.0,
            label="MOVE",
        ),
        IndicatorRegistration(
            name="ETF_Flows",
            category="flows",
            higher_change_direction="risk_appetite_up",
            lower_change_direction="risk_appetite_down",
            threshold=0.2,
            label="ETF资金流",
        ),
        IndicatorRegistration(
            name="Fed_Balance_Sheet",
            category="liquidity",
            higher_change_direction="liquidity_expansion",
            lower_change_direction="liquidity_tightening",
            threshold=1.0,
            label="美联储资产负债表",
        ),
        IndicatorRegistration(
            name="RRP",
            category="liquidity",
            higher_change_direction="liquidity_tightening",
            lower_change_direction="liquidity_expansion",
            threshold=1.0,
            label="隔夜逆回购",
        ),
        IndicatorRegistration(
            name="NASDAQ_vs_SPX",
            category="equity_structure",
            higher_change_direction="risk_appetite_up",
            lower_change_direction="risk_appetite_down",
            threshold=0.1,
            label="纳指相对标普",
        ),
        IndicatorRegistration(
            name="Russell_vs_SPX",
            category="equity_structure",
            higher_change_direction="risk_appetite_up",
            lower_change_direction="risk_appetite_down",
            threshold=0.1,
            label="罗素相对标普",
        ),
        IndicatorRegistration(
            name="Mag7_vs_EqualWeight",
            category="equity_structure",
            higher_change_direction="valuation_pressure",
            lower_change_direction="risk_appetite_down",
            threshold=0.1,
            label="Mag7相对等权",
        ),
    ]:
        registry.register_indicator(indicator)

    registry.register_asset(
        AssetRegistration(
            symbol="MSFT",
            role="长久期成长资产与AI拥挤交易标的",
            sensitivities=["实际利率", "风险偏好", "Mag7内部轮动"],
            mechanism_template=(
                "{symbol}作为{role}，核心传导是利率变化先改变折现率，"
                "再推动估值调整；当{liquidity_phrase}并带来{risk_phrase}时，"
                "资金会在Mag7内部重新比较确定性、拥挤度与估值弹性，"
                "因此个股反应本质上来自长久期现金流估值和AI拥挤交易的边际资金再分配。"
            ),
        )
    )
    registry.register_asset(
        AssetRegistration(
            symbol="ATXI",
            role="小盘高β低流动性资产",
            sensitivities=["流动性", "风险偏好", "被动资金流"],
            mechanism_template=(
                "{symbol}作为{role}，核心传导是{liquidity_phrase}先压低风险偏好，"
                "随后小盘和低流动性资产更容易遭遇被动抛售与做市深度下降，"
                "资金撤离会放大价格冲击和日内波动；因此它的主要矛盾不是单一基本面，"
                "而是流动性收缩阶段资金承接能力变弱。"
            ),
        )
    )
    return registry
