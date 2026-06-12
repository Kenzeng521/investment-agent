from __future__ import annotations

from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import requests
from loguru import logger

from schemas import MarketSnapshot, Quote


class MarketDataClient:
    def __init__(self, timeout_seconds: int = 3, max_workers: int = 8):
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers

    def get_market_snapshot(self, symbols: Iterable[str]) -> MarketSnapshot:
        quotes = {symbol: quote for symbol, quote in self.get_quotes(symbols).items()}
        indices = self.get_index_performance()
        sector_performance = self.get_sector_performance()
        return MarketSnapshot(
            as_of=date.today(),
            indices=indices,
            quotes=quotes,
            sector_performance=sector_performance,
        )

    def get_quotes(self, symbols: Iterable[str]) -> dict[str, Quote]:
        result: dict[str, Quote] = {}
        normalized = [s.upper() for s in symbols if s]
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(normalized)))) as executor:
            futures = {executor.submit(self._fetch_stooq_quote, symbol): symbol for symbol in normalized}
            for future in as_completed(futures):
                symbol = futures[future]
                quote = future.result()
                if quote:
                    result[symbol] = quote
        return result

    def get_index_performance(self) -> dict[str, Quote]:
        mapping = {"SPY": "S&P 500", "QQQ": "NASDAQ 100", "DIA": "Dow Jones"}
        quotes = self.get_quotes(mapping.keys())
        return {name: quotes[symbol] for symbol, name in mapping.items() if symbol in quotes}

    def get_sector_performance(self) -> dict[str, float]:
        etfs = {
            "Semiconductors": "SMH",
            "Cloud Computing": "WCLD",
            "Cybersecurity": "HACK",
            "Robotics": "BOTZ",
            "Autonomous Driving": "DRIV",
            "Nuclear Energy": "URA",
            "Data Centers": "VPN",
            "Power Infrastructure": "PAVE",
            "AI Compute": "AIQ",
        }
        quotes = self.get_quotes(etfs.values())
        return {sector: quotes[ticker].change_pct for sector, ticker in etfs.items() if ticker in quotes}

    def _fetch_stooq_quote(self, symbol: str) -> Quote | None:
        url = f"https://stooq.com/q/l/?s={symbol.lower()}.us&f=sd2t2ohlcv&h&e=csv"
        try:
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            lines = [line for line in response.text.splitlines() if line.strip()]
            if len(lines) < 2:
                return None
            fields = lines[1].split(",")
            close = float(fields[6]) if fields[6] != "N/D" else 0.0
            open_price = float(fields[3]) if fields[3] != "N/D" else close
            change_pct = round(((close / open_price) - 1) * 100, 2) if open_price else 0.0
            volume = float(fields[7]) if fields[7] != "N/D" else 0.0
            return Quote(symbol=symbol, price=close, change_pct=change_pct, volume=volume, source="stooq")
        except Exception as exc:
            logger.debug("Quote fetch failed for {}: {}", symbol, exc)
            return None
