from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str
    name: str = ""
    quantity: float
    cost_price: float
    market_price: float
    market_value: float
    unrealized_pl: float = 0.0
    unrealized_pl_pct: float = 0.0
    sector: str = "Unknown"


class AccountSnapshot(BaseModel):
    cash: float = 0.0
    total_assets: float = 0.0
    positions: List[Position] = Field(default_factory=list)
    currency: str = "USD"
    broker: str = "moomoo"


class Quote(BaseModel):
    symbol: str
    price: float
    change_pct: float = 0.0
    volume: float = 0.0
    source: str = "unknown"


class MarketSnapshot(BaseModel):
    as_of: date
    indices: Dict[str, Quote] = Field(default_factory=dict)
    quotes: Dict[str, Quote] = Field(default_factory=dict)
    sector_performance: Dict[str, float] = Field(default_factory=dict)


class NewsItem(BaseModel):
    title: str
    url: str = ""
    source: str = ""
    published_at: str = ""
    summary: str = ""
    symbols: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)


class MarketEvent(BaseModel):
    title: str
    url: str = ""
    source: str = ""
    published_at: str = ""
    category: str = "市场事件"
    symbols: List[str] = Field(default_factory=list)
    importance_score: int = 50
    impact: str = "中性"
    rationale: str = ""
    verification_status: str = "需验证"
    verification_score: int = 50
    verification_reason: str = ""


class EquityCandidate(BaseModel):
    symbol: str
    name: str = ""
    sector: str = "Unknown"
    status: str = "观察"
    score: int = 50
    event_count: int = 0
    rationale: str = ""
    latest_events: List[str] = Field(default_factory=list)


class SectorScore(BaseModel):
    name: str
    heat_score: int
    capital_flow_score: int
    growth_score: int
    total_score: int
    rationale: str = ""


class PositionRisk(BaseModel):
    symbol: str
    current_price: float
    cost_price: float
    pnl_pct: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_level: str
    position_risk: str


class PortfolioAnalysis(BaseModel):
    account_score: int
    position_score: int
    sector_concentration_score: int
    risk_score: int
    sector_weights: Dict[str, float] = Field(default_factory=dict)
    summary: str = ""


class AgentRunResult(BaseModel):
    report_markdown: str
    account: AccountSnapshot
    portfolio: PortfolioAnalysis
    position_risks: List[PositionRisk]
    sector_scores: List[SectorScore]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventRadarRunResult(BaseModel):
    report_markdown: str
    events: List[MarketEvent]
    candidates: List[EquityCandidate]
    metadata: Dict[str, Any] = Field(default_factory=dict)
