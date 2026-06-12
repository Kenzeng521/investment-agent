from __future__ import annotations

from typing import Iterable, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from loguru import logger

from schemas import NewsItem


class NewsFetcher:
    def __init__(self, timeout_seconds: int = 3, max_workers: int = 8):
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers

    def fetch(self, symbols: Iterable[str], topics: Iterable[str]) -> List[NewsItem]:
        items: List[NewsItem] = []
        tasks = []
        for symbol in symbols:
            tasks.append(("symbol", symbol))
        for topic in topics:
            tasks.append(("topic", topic))
        with ThreadPoolExecutor(max_workers=min(self.max_workers, max(1, len(tasks)))) as executor:
            futures = []
            for kind, value in tasks:
                if kind == "symbol":
                    futures.append(executor.submit(self.fetch_symbol_news, value))
                else:
                    futures.append(executor.submit(self.fetch_topic_news, value))
            for future in as_completed(futures):
                items.extend(future.result())
        deduped: dict[str, NewsItem] = {}
        for item in items:
            deduped[item.title] = item
        return list(deduped.values())[:80]

    def fetch_symbol_news(self, symbol: str) -> List[NewsItem]:
        return self._fetch_yahoo_rss(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US", [symbol])

    def fetch_topic_news(self, topic: str) -> List[NewsItem]:
        query = topic.replace(" ", "%20")
        return self._fetch_yahoo_rss(f"https://news.google.com/rss/search?q={query}%20stocks%20when:2d&hl=en-US&gl=US&ceid=US:en", [])

    def _fetch_yahoo_rss(self, url: str, symbols: List[str]) -> List[NewsItem]:
        try:
            response = requests.get(url, timeout=self.timeout_seconds)
            response.raise_for_status()
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.text)
            items = []
            for node in root.findall(".//item")[:10]:
                title = node.findtext("title", default="")
                link = node.findtext("link", default="")
                published = node.findtext("pubDate", default="")
                source = "rss"
                if title:
                    items.append(
                        NewsItem(
                            title=title,
                            url=link,
                            source=source,
                            published_at=published,
                            symbols=symbols,
                        )
                    )
            return items
        except Exception as exc:
            logger.debug("News fetch failed for {}: {}", url, exc)
            return []
