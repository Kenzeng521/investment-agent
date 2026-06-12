from __future__ import annotations

import socket
from typing import Iterable, List

from loguru import logger

from config import Settings
from schemas import AccountSnapshot, Position, Quote


class MoomooQueryError(RuntimeError):
    """Raised when OpenD is reachable but a Moomoo query fails."""


class MoomooClient:
    """Thin wrapper around Moomoo OpenAPI with safe empty fallbacks."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def get_account_snapshot(self) -> AccountSnapshot:
        if not self.settings.moomoo_enabled:
            logger.warning("MOOMOO_ENABLED=false; skip Moomoo OpenAPI connection")
            return AccountSnapshot(cash=0, total_assets=0, positions=[])
        if not self._is_opend_reachable():
            logger.error(
                "Moomoo OpenD is not reachable at {}:{}; start OpenD and unlock trade first",
                self.settings.moomoo_host,
                self.settings.moomoo_port,
            )
            return AccountSnapshot(cash=0, total_assets=0, positions=[])
        try:
            import moomoo as ft
        except ImportError:
            logger.warning("moomoo-api is not installed; returning empty account snapshot")
            return AccountSnapshot(cash=0, total_assets=0, positions=[])

        quote_ctx = None
        last_error = ""
        try:
            quote_ctx = ft.OpenQuoteContext(
                host=self.settings.moomoo_host,
                port=self.settings.moomoo_port,
            )
            for security_firm in self._security_firm_candidates(ft):
                trade_ctx = None
                try:
                    logger.info("Trying Moomoo security_firm={}", security_firm)
                    trade_ctx = ft.OpenSecTradeContext(
                        filter_trdmarket=self._trade_market(ft),
                        host=self.settings.moomoo_host,
                        port=self.settings.moomoo_port,
                        security_firm=security_firm,
                    )
                    self._log_available_accounts(ft, trade_ctx, security_firm)
                    cash = self._read_cash(ft, trade_ctx)
                    positions = self._read_positions(ft, trade_ctx, quote_ctx)
                    total_assets = cash + sum(p.market_value for p in positions)
                    logger.info("Moomoo account snapshot loaded with security_firm={}", security_firm)
                    return AccountSnapshot(
                        cash=cash,
                        total_assets=round(total_assets, 2),
                        positions=positions,
                    )
                except MoomooQueryError as exc:
                    last_error = str(exc)
                    logger.warning(
                        "Moomoo security_firm={} is not usable for this account: {}",
                        security_firm,
                        exc,
                    )
                finally:
                    if trade_ctx is not None:
                        trade_ctx.close()
            logger.error("No usable Moomoo security_firm found. Last error: {}", last_error)
            return AccountSnapshot(cash=0, total_assets=0, positions=[])
        except Exception as exc:
            logger.exception("Failed to read Moomoo account snapshot: {}", exc)
            return AccountSnapshot(cash=0, total_assets=0, positions=[])
        finally:
            if quote_ctx is not None:
                quote_ctx.close()

    def _read_cash(self, ft, trade_ctx) -> float:
        ret, data = trade_ctx.accinfo_query(trd_env=self._trade_env(ft))
        if ret != ft.RET_OK:
            raise MoomooQueryError(f"accinfo_query failed: {data}")
        for field in ("cash", "power", "total_assets"):
            if field in data.columns:
                return float(data.iloc[0][field])
        return 0.0

    def _read_positions(self, ft, trade_ctx, quote_ctx) -> List[Position]:
        ret, data = trade_ctx.position_list_query(trd_env=self._trade_env(ft))
        if ret != ft.RET_OK:
            raise MoomooQueryError(f"position_list_query failed: {data}")
        positions: List[Position] = []
        for _, row in data.iterrows():
            symbol = str(row.get("code", "")).replace("US.", "")
            qty = float(row.get("qty", row.get("can_sell_qty", 0)) or 0)
            cost = float(row.get("cost_price", row.get("average_cost", 0)) or 0)
            price = float(row.get("nominal_price", row.get("market_val", 0)) or 0)
            if price <= 0 and symbol:
                price = self.get_quotes([symbol]).get(symbol, Quote(symbol=symbol, price=0)).price
            market_value = round(qty * price, 2)
            pnl = round((price - cost) * qty, 2) if cost else 0.0
            pnl_pct = round(((price / cost) - 1) * 100, 2) if cost else 0.0
            positions.append(
                Position(
                    symbol=symbol,
                    name=str(row.get("stock_name", symbol)),
                    quantity=qty,
                    cost_price=cost,
                    market_price=price,
                    market_value=market_value,
                    unrealized_pl=pnl,
                    unrealized_pl_pct=pnl_pct,
                )
            )
        return positions

    def get_quotes(self, symbols: Iterable[str]) -> dict[str, Quote]:
        if not self.settings.moomoo_enabled:
            logger.warning("MOOMOO_ENABLED=false; skip Moomoo realtime quotes")
            return {}
        if not self._is_opend_reachable():
            logger.error(
                "Moomoo OpenD is not reachable at {}:{}; skip Moomoo realtime quotes",
                self.settings.moomoo_host,
                self.settings.moomoo_port,
            )
            return {}
        symbols = [s.upper().replace("US.", "") for s in symbols if s]
        if not symbols:
            return {}
        try:
            import moomoo as ft
        except ImportError:
            logger.warning("moomoo-api is not installed; cannot fetch realtime quotes")
            return {}

        ctx = None
        try:
            ctx = ft.OpenQuoteContext(host=self.settings.moomoo_host, port=self.settings.moomoo_port)
            codes = [f"US.{symbol}" for symbol in symbols]
            ret, data = ctx.get_market_snapshot(codes)
            if ret != ft.RET_OK:
                logger.warning("Moomoo get_market_snapshot failed: {}", data)
                return {}
            quotes: dict[str, Quote] = {}
            for _, row in data.iterrows():
                symbol = str(row.get("code", "")).replace("US.", "")
                quotes[symbol] = Quote(
                    symbol=symbol,
                    price=float(row.get("last_price", 0) or 0),
                    change_pct=float(row.get("change_rate", 0) or 0),
                    volume=float(row.get("volume", 0) or 0),
                    source="moomoo",
                )
            return quotes
        except Exception as exc:
            logger.exception("Failed to fetch Moomoo quotes: {}", exc)
            return {}
        finally:
            if ctx is not None:
                ctx.close()

    def _trade_env(self, ft):
        return ft.TrdEnv.REAL if self.settings.moomoo_trade_env.upper() == "REAL" else ft.TrdEnv.SIMULATE

    def _trade_market(self, ft):
        market = self.settings.moomoo_market.upper()
        return getattr(ft.TrdMarket, market, ft.TrdMarket.US)

    def _security_firm_candidates(self, ft) -> List[str]:
        configured = (self.settings.moomoo_security_firm or "AUTO").strip().upper()
        if configured != "AUTO":
            return [self._resolve_security_firm(ft, configured)]

        names = [
            "FUTUINC",
            "FUTUSG",
            "FUTUSECURITIES",
            "FUTUMY",
            "FUTUJP",
            "FUTUAU",
            "FUTUCA",
        ]
        return [self._resolve_security_firm(ft, name) for name in names]

    def _resolve_security_firm(self, ft, name: str) -> str:
        return getattr(ft.SecurityFirm, name, name)

    def _log_available_accounts(self, ft, trade_ctx, security_firm: str) -> None:
        ret, data = trade_ctx.get_acc_list()
        if ret != ft.RET_OK:
            logger.warning("Moomoo get_acc_list failed for security_firm={}: {}", security_firm, data)
            return
        summary = self._available_account_summary(data)
        if summary:
            logger.info("Moomoo available accounts for security_firm={}: {}", security_firm, summary)
        else:
            logger.warning("Moomoo get_acc_list returned no accounts for security_firm={}", security_firm)

    def _available_account_summary(self, data) -> str:
        if data is None or getattr(data, "empty", True):
            return ""
        parts: List[str] = []
        for _, row in data.iterrows():
            auth = row.get("trdmarket_auth", "")
            if isinstance(auth, list):
                auth_text = "[" + ",".join(str(item) for item in auth) + "]"
            else:
                auth_text = str(auth)
            parts.append(
                "/".join(
                    [
                        str(row.get("acc_id", "N/A")),
                        str(row.get("trd_env", "N/A")),
                        str(row.get("acc_type", "N/A")),
                        auth_text,
                        str(row.get("acc_status", "N/A")),
                    ]
                )
            )
        return "; ".join(parts)

    def _is_opend_reachable(self) -> bool:
        try:
            with socket.create_connection(
                (self.settings.moomoo_host, self.settings.moomoo_port),
                timeout=2,
            ):
                return True
        except OSError:
            return False

    def submit_order_requires_confirmation(self, *args, **kwargs) -> None:
        if not self.settings.auto_trading:
            raise PermissionError("AUTO_TRADING=false; automatic order placement is disabled")
        if self.settings.require_human_confirm:
            raise PermissionError("Human confirmation is required before order placement")
        raise NotImplementedError("Order placement is intentionally not implemented in the default build")
