from __future__ import annotations

from collections import defaultdict

from schemas import AccountSnapshot, PortfolioAnalysis


class PortfolioAnalyzer:
    def analyze(self, snapshot: AccountSnapshot) -> PortfolioAnalysis:
        total_assets = snapshot.total_assets or (snapshot.cash + sum(p.market_value for p in snapshot.positions))
        invested = sum(p.market_value for p in snapshot.positions)
        cash_ratio = snapshot.cash / total_assets if total_assets else 1.0
        sector_weights = self._sector_weights(snapshot, invested)

        account_score = self._bounded_score(60 + cash_ratio * 20 + min(len(snapshot.positions), 8) * 2)
        position_score = self._position_score(snapshot)
        concentration_score = self._concentration_score(sector_weights)
        risk_score = self._risk_score(snapshot, cash_ratio, sector_weights)

        summary = self._summary(snapshot, cash_ratio, sector_weights)
        return PortfolioAnalysis(
            account_score=account_score,
            position_score=position_score,
            sector_concentration_score=concentration_score,
            risk_score=risk_score,
            sector_weights=sector_weights,
            summary=summary,
        )

    def _sector_weights(self, snapshot: AccountSnapshot, invested: float) -> dict[str, float]:
        weights = defaultdict(float)
        if invested <= 0:
            return {}
        for position in snapshot.positions:
            weights[position.sector or "Unknown"] += position.market_value / invested
        return {sector: round(weight, 4) for sector, weight in sorted(weights.items())}

    def _position_score(self, snapshot: AccountSnapshot) -> int:
        if not snapshot.positions:
            return 70
        avg_pnl = sum(p.unrealized_pl_pct for p in snapshot.positions) / len(snapshot.positions)
        loss_penalty = sum(8 for p in snapshot.positions if p.unrealized_pl_pct < -8)
        return self._bounded_score(72 + avg_pnl * 0.6 - loss_penalty)

    def _concentration_score(self, weights: dict[str, float]) -> int:
        if not weights:
            return 70
        max_weight = max(weights.values())
        if max_weight <= 0.35:
            return 90
        if max_weight <= 0.5:
            return 78
        if max_weight <= 0.7:
            return 62
        return 45

    def _risk_score(self, snapshot: AccountSnapshot, cash_ratio: float, weights: dict[str, float]) -> int:
        drawdown_penalty = sum(max(0, -p.unrealized_pl_pct) for p in snapshot.positions) * 0.8
        concentration_penalty = max(0, (max(weights.values()) - 0.45) * 60) if weights else 0
        cash_bonus = min(12, cash_ratio * 20)
        return self._bounded_score(80 + cash_bonus - drawdown_penalty - concentration_penalty)

    def _summary(self, snapshot: AccountSnapshot, cash_ratio: float, weights: dict[str, float]) -> str:
        if not snapshot.positions:
            return "当前未读取到持仓，系统不会给出主动交易建议。"
        max_sector = max(weights.items(), key=lambda item: item[1]) if weights else ("Unknown", 0)
        return (
            f"当前持仓 {len(snapshot.positions)} 只，现金比例 {cash_ratio:.1%}，"
            f"最大行业为 {max_sector[0]}（{max_sector[1]:.1%}）。"
        )

    def _bounded_score(self, value: float) -> int:
        return int(max(0, min(100, round(value))))
