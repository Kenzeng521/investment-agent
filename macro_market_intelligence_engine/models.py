from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


Regime = Literal["Risk-On", "Repricing", "Risk-Off"]
SignalDirection = Literal[
    "liquidity_expansion",
    "liquidity_tightening",
    "risk_appetite_up",
    "risk_appetite_down",
    "valuation_support",
    "valuation_pressure",
    "neutral",
]


class MacroIndicatorReading(BaseModel):
    name: str
    value: float
    change: float = 0.0
    unit: str = ""
    note: str = ""


class MacroSnapshot(BaseModel):
    as_of: str
    indicators: List[MacroIndicatorReading] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class IndicatorRegistration(BaseModel):
    name: str
    category: str
    higher_change_direction: SignalDirection
    lower_change_direction: SignalDirection
    threshold: float = 0.0
    label: str = ""


class AssetRegistration(BaseModel):
    symbol: str
    role: str
    sensitivities: List[str] = Field(default_factory=list)
    mechanism_template: str


class InterpretedSignal(BaseModel):
    name: str
    category: str
    direction: SignalDirection
    strength: float
    description: str


class MarketRegimeSection(BaseModel):
    regime: Regime
    reason: str


class SignalSummary(BaseModel):
    liquidity_score: float
    risk_appetite_score: float
    valuation_score: float
    evidence_count: int
    dominant_signals: List[str] = Field(default_factory=list)
    stress_categories: List[str] = Field(default_factory=list)


class AssetImpact(BaseModel):
    symbol: str
    role: str
    impact_path: str
    position_bias: str


class MacroMarketIntelligenceReport(BaseModel):
    as_of: str
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(timespec="seconds") + "Z")
    market_regime: MarketRegimeSection
    flow_narrative: str
    asset_impacts: Dict[str, AssetImpact]
    position_preference: str
    signal_summary: SignalSummary

    def to_json_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "generated_at": self.generated_at,
            "market_regime": self.market_regime.model_dump(),
            "flow_narrative": self.flow_narrative,
            "asset_impact": {
                "assets": {symbol: impact.model_dump() for symbol, impact in self.asset_impacts.items()},
                "position_preference": self.position_preference,
            },
            "signal_summary": self.signal_summary.model_dump(),
        }

    def to_wechat_text(self) -> str:
        asset_lines = [
            f"{symbol}：{impact.impact_path} 当前偏好：{impact.position_bias}"
            for symbol, impact in self.asset_impacts.items()
        ]
        return "\n\n".join(
            [
                f"Market Regime：{self.market_regime.regime}。{self.market_regime.reason}",
                f"Flow Narrative：{self.flow_narrative}",
                "Asset Impact："
                + "\n"
                + "\n".join(asset_lines)
                + f"\n仓位偏好：{self.position_preference}",
            ]
        )
