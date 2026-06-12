from __future__ import annotations

from config import load_settings
from schemas import AccountSnapshot, Position, PositionRisk


class RiskEngine:
    def __init__(
        self,
        stop_loss_pct: float = 0.10,
        take_profit_1_pct: float = 0.10,
        take_profit_2_pct: float = 0.20,
        auto_trading_enabled: bool | None = None,
    ):
        settings = load_settings()
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_1_pct = take_profit_1_pct
        self.take_profit_2_pct = take_profit_2_pct
        self.auto_trading_enabled = settings.auto_trading if auto_trading_enabled is None else auto_trading_enabled

    def analyze_account(self, snapshot: AccountSnapshot) -> list[PositionRisk]:
        return [self.analyze_position(position) for position in snapshot.positions]

    def analyze_position(self, position: Position) -> PositionRisk:
        price = position.market_price
        cost = position.cost_price
        pnl_pct = position.unrealized_pl_pct
        stop_base = max(cost, price) if pnl_pct > 12 else cost
        stop_loss = round(stop_base * (1 - self.stop_loss_pct), 2)
        take_profit_1 = round(price * (1 + self.take_profit_1_pct), 2)
        take_profit_2 = round(price * (1 + self.take_profit_2_pct), 2)
        risk_level = self._risk_level(pnl_pct, price, stop_loss)
        position_risk = self._position_risk(position)
        return PositionRisk(
            symbol=position.symbol,
            current_price=round(price, 2),
            cost_price=round(cost, 2),
            pnl_pct=round(pnl_pct, 2),
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            risk_level=risk_level,
            position_risk=position_risk,
        )

    def _risk_level(self, pnl_pct: float, price: float, stop_loss: float) -> str:
        distance_to_stop = ((price - stop_loss) / price) * 100 if price else 100
        if pnl_pct <= -12 or distance_to_stop <= 3:
            return "HIGH"
        if pnl_pct <= -5 or distance_to_stop <= 8:
            return "MEDIUM"
        return "LOW"

    def _position_risk(self, position: Position) -> str:
        if position.unrealized_pl_pct <= -15:
            return "LOSS_CONTROL_REQUIRED"
        if position.unrealized_pl_pct >= 30:
            return "PROFIT_PROTECTION_REQUIRED"
        return "NORMAL"
