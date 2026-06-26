from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Sequence

from analysis.fact_verifier import FactVerifier
from schemas import EquityCandidate, MarketEvent, NewsItem


POSITIVE_KEYWORDS = {
    "ai": 12,
    "artificial intelligence": 12,
    "data center": 10,
    "nvidia": 10,
    "semiconductor": 9,
    "chip": 8,
    "cloud": 8,
    "cybersecurity": 8,
    "robot": 7,
    "autonomous": 7,
    "nuclear": 7,
    "power": 6,
    "upgrade": 7,
    "raises": 6,
    "beats": 8,
    "guidance": 6,
    "contract": 7,
    "partnership": 8,
    "ipo": 10,
    "files for ipo": 14,
    "debut": 9,
    "acquisition": 8,
    "merger": 8,
}

RISK_KEYWORDS = {
    "probe": -8,
    "investigation": -8,
    "downgrade": -7,
    "misses": -8,
    "cuts guidance": -10,
    "lawsuit": -7,
    "tariff": -5,
}

CATEGORY_BASE_SCORE = {
    "AI算力": 70,
    "半导体": 66,
    "数据中心": 64,
    "云计算": 62,
    "网络安全": 62,
    "机器人": 60,
    "自动驾驶": 60,
    "电力基础设施": 58,
    "核能": 58,
    "IPO": 65,
}

TICKER_NAMES = {
    "AAPL": "Apple",
    "ABBV": "AbbVie",
    "AMD": "Advanced Micro Devices",
    "AMAT": "Applied Materials",
    "AMZN": "Amazon",
    "ANET": "Arista Networks",
    "ARM": "Arm Holdings",
    "ASML": "ASML",
    "AVGO": "Broadcom",
    "CEG": "Constellation Energy",
    "CRWD": "CrowdStrike",
    "CRWV": "CoreWeave",
    "ETN": "Eaton",
    "FTNT": "Fortinet",
    "GOOGL": "Alphabet",
    "LRCX": "Lam Research",
    "MBLY": "Mobileye",
    "META": "Meta Platforms",
    "MSFT": "Microsoft",
    "NEE": "NextEra Energy",
    "NOW": "ServiceNow",
    "NVDA": "Nvidia",
    "ORCL": "Oracle",
    "PANW": "Palo Alto Networks",
    "PWR": "Quanta Services",
    "SMCI": "Super Micro Computer",
    "TSLA": "Tesla",
    "VRT": "Vertiv",
    "VST": "Vistra",
    "ZS": "Zscaler",
}


class EventAnalyzer:
    def __init__(self, candidate_universe: Sequence[str] | None = None):
        self.candidate_universe = {symbol.upper() for symbol in (candidate_universe or [])}
        self.fact_verifier = FactVerifier()

    def analyze(self, news: Iterable[NewsItem]) -> tuple[List[MarketEvent], List[EquityCandidate]]:
        events = [self._score_event(item) for item in news if item.title]
        events = sorted(events, key=lambda item: item.importance_score, reverse=True)[:40]
        return events, self._build_candidates(events)

    def _score_event(self, item: NewsItem) -> MarketEvent:
        category = item.categories[0] if item.categories else self._infer_category(item.title)
        text = item.title.lower()
        score = CATEGORY_BASE_SCORE.get(category, 50)
        reasons: List[str] = []
        for keyword, weight in POSITIVE_KEYWORDS.items():
            if keyword in text:
                score += weight
                reasons.append(keyword)
        for keyword, weight in RISK_KEYWORDS.items():
            if keyword in text:
                score += weight
                reasons.append(keyword)
        if item.symbols:
            score += 5
        score = max(0, min(100, score))
        impact = "利好" if score >= 70 else "风险" if score <= 45 else "中性"
        rationale = "、".join(reasons[:4]) if reasons else "主题相关新闻，需进一步验证对收入、订单或估值的影响"
        verification = self.fact_verifier.verify(item)
        return MarketEvent(
            title=item.title,
            url=item.url,
            source=item.source,
            published_at=item.published_at,
            category=category,
            symbols=[symbol.upper() for symbol in item.symbols],
            importance_score=score,
            impact=impact,
            rationale=rationale,
            verification_status=verification.status,
            verification_score=verification.score,
            verification_reason=verification.reason,
        )

    def _infer_category(self, title: str) -> str:
        text = title.lower()
        if "ipo" in text or "debut" in text:
            return "IPO"
        if "cyber" in text or "security" in text:
            return "网络安全"
        if "semiconductor" in text or "chip" in text:
            return "半导体"
        if "data center" in text or "ai" in text or "nvidia" in text:
            return "AI算力"
        return "市场事件"

    def _build_candidates(self, events: List[MarketEvent]) -> List[EquityCandidate]:
        grouped: dict[str, list[MarketEvent]] = defaultdict(list)
        for event in events:
            for symbol in event.symbols:
                if not self.candidate_universe or symbol in self.candidate_universe:
                    grouped[symbol].append(event)
        candidates: List[EquityCandidate] = []
        for symbol, symbol_events in grouped.items():
            avg_score = round(sum(event.importance_score for event in symbol_events) / len(symbol_events))
            status = "重点跟踪" if avg_score >= 80 else "跟踪候选" if avg_score >= 65 else "观察"
            categories = [event.category for event in symbol_events if event.category]
            sector = categories[0] if categories else "Unknown"
            candidates.append(
                EquityCandidate(
                    symbol=symbol,
                    name=TICKER_NAMES.get(symbol, ""),
                    sector=sector,
                    status=status,
                    score=int(avg_score),
                    event_count=len(symbol_events),
                    rationale="; ".join(event.rationale for event in symbol_events[:2]),
                    latest_events=[event.title for event in symbol_events[:3]],
                )
            )
        return sorted(candidates, key=lambda item: (item.score, item.event_count), reverse=True)[:20]
