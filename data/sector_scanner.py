from __future__ import annotations

from typing import Dict, Iterable, List

from schemas import NewsItem, SectorScore


DEFAULT_SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "AI算力": ["AI", "GPU", "accelerator", "inference", "training"],
    "半导体": ["semiconductor", "chip", "wafer", "foundry", "HBM"],
    "电力基础设施": ["power grid", "utility", "electrification", "transmission"],
    "数据中心": ["data center", "colocation", "server", "cooling"],
    "云计算": ["cloud", "Azure", "AWS", "Google Cloud", "SaaS"],
    "核能": ["nuclear", "uranium", "SMR", "reactor"],
    "机器人": ["robot", "automation", "industrial automation"],
    "自动驾驶": ["autonomous", "ADAS", "robotaxi", "self-driving"],
    "网络安全": ["cybersecurity", "security", "zero trust", "breach"],
    "新兴科技": ["quantum", "spatial computing", "edge AI", "biotech"],
}


class SectorScanner:
    def __init__(self, sector_keywords: Dict[str, List[str]] | None = None):
        self.sector_keywords = sector_keywords or DEFAULT_SECTOR_KEYWORDS

    def scan(self, news: Iterable[NewsItem], sector_performance: Dict[str, float] | None = None) -> List[SectorScore]:
        news_items = list(news)
        performance = sector_performance or {}
        scores: List[SectorScore] = []
        for sector, keywords in self.sector_keywords.items():
            mentions = self._count_mentions(news_items, keywords)
            perf = self._matching_performance(sector, performance)
            heat = min(100, 45 + mentions * 8)
            capital = max(0, min(100, int(50 + perf * 7)))
            growth = self._growth_baseline(sector)
            total = round(heat * 0.3 + capital * 0.3 + growth * 0.4)
            rationale = f"新闻提及 {mentions} 次，相关ETF/行业表现 {perf:.2f}%。"
            scores.append(
                SectorScore(
                    name=sector,
                    heat_score=int(heat),
                    capital_flow_score=int(capital),
                    growth_score=int(growth),
                    total_score=int(total),
                    rationale=rationale,
                )
            )
        return sorted(scores, key=lambda item: item.total_score, reverse=True)

    def _count_mentions(self, news: List[NewsItem], keywords: List[str]) -> int:
        count = 0
        lowered = [keyword.lower() for keyword in keywords]
        for item in news:
            haystack = f"{item.title} {item.summary}".lower()
            if any(keyword.lower() in haystack for keyword in lowered):
                count += 1
        return count

    def _matching_performance(self, sector: str, performance: Dict[str, float]) -> float:
        aliases = {
            "AI算力": "AI Compute",
            "半导体": "Semiconductors",
            "电力基础设施": "Power Infrastructure",
            "数据中心": "Data Centers",
            "云计算": "Cloud Computing",
            "核能": "Nuclear Energy",
            "机器人": "Robotics",
            "自动驾驶": "Autonomous Driving",
            "网络安全": "Cybersecurity",
        }
        return float(performance.get(aliases.get(sector, sector), 0.0))

    def _growth_baseline(self, sector: str) -> int:
        baselines = {
            "AI算力": 88,
            "半导体": 84,
            "电力基础设施": 78,
            "数据中心": 82,
            "云计算": 80,
            "核能": 76,
            "机器人": 74,
            "自动驾驶": 72,
            "网络安全": 79,
            "新兴科技": 70,
        }
        return baselines.get(sector, 65)
