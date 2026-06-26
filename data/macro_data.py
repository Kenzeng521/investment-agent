from __future__ import annotations

from datetime import date
from urllib.parse import quote

import requests
from loguru import logger

from macro_market_intelligence_engine import MacroIndicatorReading, MacroSnapshot


class MacroDataClient:
    """Fetch macro-market proxy variables for the macro intelligence engine."""

    SYMBOL_MAP = {
        "10Y": "^TNX",
        "DXY": "DX-Y.NYB",
        "VIX": "^VIX",
        "QQQ": "QQQ",
        "SPY": "SPY",
        "IWM": "IWM",
    }

    def __init__(self, timeout_seconds: int = 8):
        self.timeout_seconds = timeout_seconds
        self.headers = {"User-Agent": "Mozilla/5.0 investment-agent/1.0"}

    def get_snapshot(self) -> MacroSnapshot:
        pairs = {name: self._fetch_yahoo_previous_pair(symbol) for name, symbol in self.SYMBOL_MAP.items()}
        indicators: list[MacroIndicatorReading] = []
        for name in ["10Y", "DXY", "VIX"]:
            pair = pairs.get(name)
            if pair:
                current, previous = pair
                indicators.append(
                    MacroIndicatorReading(
                        name=name,
                        value=current,
                        change=round(current - previous, 4),
                    )
                )

        qqq_spy = self._relative_change(pairs.get("QQQ"), pairs.get("SPY"))
        if qqq_spy is not None:
            indicators.append(MacroIndicatorReading(name="NASDAQ_vs_SPX", value=qqq_spy, change=qqq_spy))
        iwm_spy = self._relative_change(pairs.get("IWM"), pairs.get("SPY"))
        if iwm_spy is not None:
            indicators.append(MacroIndicatorReading(name="Russell_vs_SPX", value=iwm_spy, change=iwm_spy))

        if len(indicators) < 3:
            logger.warning("Macro data incomplete; using neutral macro snapshot")
            return self.neutral_snapshot()
        return MacroSnapshot(
            as_of=date.today().isoformat(),
            indicators=indicators,
            metadata={"source": "yahoo-chart", "note": "ETF flows use market-structure proxies until a flow API is configured."},
        )

    def _fetch_yahoo_previous_pair(self, symbol: str) -> tuple[float, float] | None:
        encoded = quote(symbol, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
        try:
            response = requests.get(url, timeout=self.timeout_seconds, headers=self.headers)
            response.raise_for_status()
            result = response.json()["chart"]["result"][0]
            closes = [value for value in result["indicators"]["quote"][0]["close"] if value is not None]
            if len(closes) < 2:
                return None
            return float(closes[-1]), float(closes[-2])
        except Exception as exc:
            logger.debug("Macro data fetch failed for {}: {}", symbol, exc.__class__.__name__)
            return None

    def _relative_change(
        self, numerator: tuple[float, float] | None, denominator: tuple[float, float] | None
    ) -> float | None:
        if not numerator or not denominator:
            return None
        numerator_current, numerator_previous = numerator
        denominator_current, denominator_previous = denominator
        if not numerator_previous or not denominator_previous:
            return None
        numerator_change = (numerator_current / numerator_previous - 1) * 100
        denominator_change = (denominator_current / denominator_previous - 1) * 100
        return round(numerator_change - denominator_change, 4)

    @staticmethod
    def neutral_snapshot(as_of: str | None = None) -> MacroSnapshot:
        return MacroSnapshot(
            as_of=as_of or date.today().isoformat(),
            indicators=[
                MacroIndicatorReading(name="10Y", value=0.0, change=0.0),
                MacroIndicatorReading(name="DXY", value=0.0, change=0.0),
                MacroIndicatorReading(name="VIX", value=0.0, change=0.0),
            ],
            metadata={"source": "neutral-fallback"},
        )
