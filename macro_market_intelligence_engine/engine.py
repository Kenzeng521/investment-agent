from __future__ import annotations

from .models import (
    AssetImpact,
    InterpretedSignal,
    MacroIndicatorReading,
    MacroMarketIntelligenceReport,
    MacroSnapshot,
    MarketRegimeSection,
    SignalSummary,
)
from .registry import MacroMarketRegistry, default_registry


POSITION_PREFERENCES = {
    "Risk-On": "成长 / AI / 高β偏多",
    "Repricing": "结构性轮动 / 降杠杆但保核心资产",
    "Risk-Off": "防御 / 现金优先 / 小盘回避",
}


class MacroMarketIntelligenceEngine:
    def __init__(self, registry: MacroMarketRegistry | None = None):
        self.registry = registry or default_registry()

    def analyze(self, snapshot: MacroSnapshot) -> MacroMarketIntelligenceReport:
        signals = self._interpret_signals(snapshot.indicators)
        summary = self._summarize(signals)
        regime = self._classify_regime(summary)
        flow_narrative = self._build_flow_narrative(regime.regime, summary)
        position_preference = POSITION_PREFERENCES[regime.regime]
        impacts = {
            symbol: self._build_asset_impact(symbol, regime.regime, summary, position_preference)
            for symbol in self.registry.assets
        }
        return MacroMarketIntelligenceReport(
            as_of=snapshot.as_of,
            market_regime=regime,
            flow_narrative=flow_narrative,
            asset_impacts=impacts,
            position_preference=position_preference,
            signal_summary=summary,
        )

    def _interpret_signals(self, readings: list[MacroIndicatorReading]) -> list[InterpretedSignal]:
        signals: list[InterpretedSignal] = []
        for reading in readings:
            registration = self.registry.get_indicator(reading.name)
            if not registration:
                continue
            if abs(reading.change) < registration.threshold:
                direction = "neutral"
            elif reading.change > 0:
                direction = registration.higher_change_direction
            else:
                direction = registration.lower_change_direction
            if direction == "neutral":
                continue
            strength = round(abs(reading.change) / max(registration.threshold, 0.01), 2)
            label = registration.label or reading.name
            verb = "上行" if reading.change > 0 else "下行"
            signals.append(
                InterpretedSignal(
                    name=reading.name,
                    category=registration.category,
                    direction=direction,
                    strength=min(strength, 5.0),
                    description=f"{label}{verb}，指向{_direction_text(direction)}",
                )
            )
        return signals

    def _summarize(self, signals: list[InterpretedSignal]) -> SignalSummary:
        liquidity_score = 0.0
        risk_appetite_score = 0.0
        valuation_score = 0.0
        for signal in signals:
            signed_strength = signal.strength
            if signal.direction == "liquidity_expansion":
                liquidity_score += signed_strength
            elif signal.direction == "liquidity_tightening":
                liquidity_score -= signed_strength
            elif signal.direction == "risk_appetite_up":
                risk_appetite_score += signed_strength
            elif signal.direction == "risk_appetite_down":
                risk_appetite_score -= signed_strength
            elif signal.direction == "valuation_support":
                valuation_score += signed_strength
            elif signal.direction == "valuation_pressure":
                valuation_score -= signed_strength
        dominant = [signal.description for signal in sorted(signals, key=lambda item: item.strength, reverse=True)[:5]]
        stress_categories = sorted(
            {
                signal.category
                for signal in signals
                if signal.direction in {"liquidity_tightening", "risk_appetite_down", "valuation_pressure"}
            }
        )
        return SignalSummary(
            liquidity_score=round(liquidity_score, 2),
            risk_appetite_score=round(risk_appetite_score, 2),
            valuation_score=round(valuation_score, 2),
            evidence_count=len(signals),
            dominant_signals=dominant,
            stress_categories=stress_categories,
        )

    def _classify_regime(self, summary: SignalSummary) -> MarketRegimeSection:
        liquidity = summary.liquidity_score
        risk = summary.risk_appetite_score
        valuation = summary.valuation_score
        evidence = max(summary.evidence_count, 1)
        if evidence < 3:
            return MarketRegimeSection(
                regime="Repricing",
                reason="有效证据不足三项，按中性资金环境处理，重点观察估值结构调整。",
            )
        if liquidity >= 1.5 and risk >= 1.5 and valuation >= -1.0:
            return MarketRegimeSection(
                regime="Risk-On",
                reason="多变量共振显示资金扩张、波动回落和风险偏好上升，流动性开始支持估值扩张。",
            )
        has_deleveraging_confirmation = bool({"volatility", "flows"} & set(summary.stress_categories))
        if liquidity <= -1.5 and risk <= -1.5 and has_deleveraging_confirmation:
            return MarketRegimeSection(
                regime="Risk-Off",
                reason="多变量共振显示利率/美元/波动率与资金流同时指向收紧，市场进入去杠杆和防御定价。",
            )
        return MarketRegimeSection(
            regime="Repricing",
            reason="流动性没有形成单边扩张或收缩，但利率、美元和市场结构正在推动估值结构调整。",
        )

    def _build_flow_narrative(self, regime: str, summary: SignalSummary) -> str:
        macro_phrase = _macro_phrase(summary)
        liquidity_phrase = _liquidity_phrase(summary)
        risk_phrase = _risk_phrase(summary)
        valuation_phrase = _valuation_phrase(summary)
        structure_phrase = _structure_phrase(regime)
        return (
            f"宏观变量的组合变化首先通过{macro_phrase}传导到利率和美元，"
            f"进而使市场感受到{liquidity_phrase}；流动性边际变化会改变投资者可承受的杠杆和久期，"
            f"因此风险偏好表现为{risk_phrase}，资金流随之在ETF、大小盘和拥挤成长资产之间重新分配，"
            f"最终通过{valuation_phrase}影响估值，并形成{structure_phrase}。"
        )

    def _build_asset_impact(
        self, symbol: str, regime: str, summary: SignalSummary, position_preference: str
    ) -> AssetImpact:
        registration = self.registry.get_asset(symbol)
        if not registration:
            raise KeyError(symbol)
        liquidity_phrase = _liquidity_phrase(summary)
        risk_phrase = _risk_phrase(summary)
        path = registration.mechanism_template.format(
            symbol=registration.symbol,
            role=registration.role,
            regime=regime,
            liquidity_phrase=liquidity_phrase,
            risk_phrase=risk_phrase,
        )
        return AssetImpact(
            symbol=registration.symbol,
            role=registration.role,
            impact_path=path,
            position_bias=position_preference,
        )


def _direction_text(direction: str) -> str:
    return {
        "liquidity_expansion": "流动性扩张",
        "liquidity_tightening": "流动性收紧",
        "risk_appetite_up": "风险偏好上升",
        "risk_appetite_down": "风险偏好下降",
        "valuation_support": "估值支撑",
        "valuation_pressure": "估值压力",
        "neutral": "中性",
    }[direction]


def _macro_phrase(summary: SignalSummary) -> str:
    if summary.valuation_score < -1:
        return "实际利率和折现率上行"
    if summary.valuation_score > 1:
        return "实际利率和折现率下行"
    if summary.liquidity_score < -1:
        return "美元与资金成本上行"
    if summary.liquidity_score > 1:
        return "美元走弱与资金成本下降"
    return "利率、美元和波动率的交叉变化"


def _liquidity_phrase(summary: SignalSummary) -> str:
    if summary.liquidity_score <= -1.5:
        return "流动性收紧"
    if summary.liquidity_score >= 1.5:
        return "流动性扩张"
    return "流动性稳定但边际分化"


def _risk_phrase(summary: SignalSummary) -> str:
    if summary.risk_appetite_score <= -1.5:
        return "风险偏好下降"
    if summary.risk_appetite_score >= 1.5:
        return "风险偏好上升"
    return "风险偏好分化"


def _valuation_phrase(summary: SignalSummary) -> str:
    if summary.valuation_score <= -1.0:
        return "折现率抬升压缩久期资产估值"
    if summary.valuation_score >= 1.0:
        return "折现率下行支撑久期资产估值"
    return "相对估值重估而非全面扩张"


def _structure_phrase(regime: str) -> str:
    if regime == "Risk-On":
        return "成长、AI和高β资产获得更强边际买盘"
    if regime == "Risk-Off":
        return "防御、现金和高流动性资产相对占优，小盘高β承压"
    return "结构性轮动，核心资产保留但杠杆和拥挤度下降"
