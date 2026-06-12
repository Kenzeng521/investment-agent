from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, List
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests
from loguru import logger

from schemas import NewsItem


DEFAULT_EVENT_TOPICS = {
    "AI算力": "AI data center Nvidia GPU cloud stock",
    "半导体": "semiconductor chip earnings guidance stock",
    "数据中心": "data center power demand cloud AI stock",
    "云计算": "cloud computing AI enterprise software stock",
    "电力基础设施": "power grid electricity infrastructure data center stock",
    "核能": "nuclear energy reactor data center power stock",
    "机器人": "robotics automation humanoid robot stock",
    "自动驾驶": "autonomous driving robotaxi lidar EV stock",
    "网络安全": "cybersecurity AI software breach stock",
    "IPO": "US IPO Nasdaq NYSE filing debut technology company",
}

SYMBOL_ALIASES = {
    "AAPL": ("apple",),
    "AMD": ("amd", "advanced micro devices"),
    "AMAT": ("applied materials",),
    "AMZN": ("amazon", "aws"),
    "ANET": ("arista",),
    "ARM": ("arm holdings", "arm"),
    "ASML": ("asml",),
    "AVGO": ("broadcom",),
    "CEG": ("constellation energy",),
    "CRWD": ("crowdstrike",),
    "CRWV": ("coreweave",),
    "ETN": ("eaton",),
    "FTNT": ("fortinet",),
    "GOOGL": ("alphabet", "google"),
    "LRCX": ("lam research",),
    "MBLY": ("mobileye",),
    "META": ("meta platforms", "meta"),
    "MSFT": ("microsoft", "azure"),
    "NEE": ("nextera",),
    "NOW": ("servicenow",),
    "NVDA": ("nvidia",),
    "ORCL": ("oracle",),
    "PANW": ("palo alto networks",),
    "PWR": ("quanta services",),
    "SMCI": ("super micro", "supermicro"),
    "TSLA": ("tesla",),
    "VRT": ("vertiv",),
    "VST": ("vistra",),
    "ZS": ("zscaler",),
}


class EventRadarFetcher:
    def __init__(self, timeout_seconds: int = 6, max_workers: int = 8):
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers

    def fetch(
        self,
        topics: dict[str, str] | None = None,
        symbols: Iterable[str] | None = None,
        max_items: int = 80,
    ) -> List[NewsItem]:
        topics = topics or DEFAULT_EVENT_TOPICS
        symbols = [symbol.upper() for symbol in (symbols or [])]
        tasks: list[tuple[str, str, list[str], list[str]]] = []
        for category, query in topics.items():
            tasks.append((self._google_news_url(query), "google-news", [], [category]))
        for symbol in symbols:
            query = f"{symbol} stock AI earnings guidance partnership"
            tasks.append((self._google_news_url(query), "google-news", [symbol], []))

        items: list[NewsItem] = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(tasks)))) as executor:
            futures = {
                executor.submit(self._fetch_url, url, source, task_symbols, categories): url
                for url, source, task_symbols, categories in tasks
            }
            for future in as_completed(futures):
                items.extend(future.result())

        deduped: dict[str, NewsItem] = {}
        for item in items:
            deduped[item.title] = item
        return list(deduped.values())[:max_items]

    def _fetch_url(self, url: str, source: str, symbols: list[str], categories: list[str]) -> List[NewsItem]:
        try:
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            return self._parse_rss(response.text, symbols=symbols, categories=categories, source=source)
        except Exception as exc:
            logger.debug("Event radar fetch failed for {}: {}", url, exc)
            return []

    def _parse_rss(self, xml_text: str, symbols: list[str], categories: list[str], source: str) -> List[NewsItem]:
        root = ET.fromstring(xml_text)
        items: list[NewsItem] = []
        for node in root.findall(".//item")[:12]:
            title = node.findtext("title", default="").strip()
            link = node.findtext("link", default="").strip()
            published = node.findtext("pubDate", default="").strip()
            matched_symbols = self._matched_symbols(title, symbols)
            if symbols and not matched_symbols:
                continue
            if title:
                items.append(
                    NewsItem(
                        title=title,
                        url=link,
                        source=source,
                        published_at=published,
                        symbols=matched_symbols,
                        categories=categories,
                    )
                )
        return items

    def _matched_symbols(self, title: str, symbols: list[str]) -> list[str]:
        if not symbols:
            return []
        text = title.lower()
        matched = []
        for symbol in symbols:
            symbol_upper = symbol.upper()
            aliases = (symbol_upper.lower(),) + SYMBOL_ALIASES.get(symbol_upper, ())
            if any(alias in text for alias in aliases):
                matched.append(symbol_upper)
        return matched

    def _google_news_url(self, query: str) -> str:
        return (
            "https://news.google.com/rss/search?q="
            + quote_plus(f"{query} when:2d")
            + "&hl=en-US&gl=US&ceid=US:en"
        )
