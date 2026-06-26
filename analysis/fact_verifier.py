from __future__ import annotations

from dataclasses import dataclass

from schemas import NewsItem


HIGH_TRUST_SOURCES = {
    "reuters",
    "bloomberg",
    "cnbc",
    "marketwatch",
    "associated press",
    "ap news",
    "sec",
    "pr newswire",
    "business wire",
    "globe newswire",
    "company announcement",
}

LOW_TRUST_HINTS = {
    "rumor",
    "anonymous",
    "blog",
    "stocktwits",
    "motley fool",
    "prediction",
    "will explode",
    "parabolic",
}


@dataclass(frozen=True)
class VerificationResult:
    status: str
    score: int
    reason: str


class FactVerifier:
    def verify(self, item: NewsItem) -> VerificationResult:
        source = (item.source or "").lower()
        title = (item.title or "").lower()
        if any(hint in title or hint in source for hint in LOW_TRUST_HINTS):
            return VerificationResult("低可信", 35, "标题或来源包含预测/传闻/社区噪音特征，需等待权威来源确认。")
        if any(source_name in source for source_name in HIGH_TRUST_SOURCES):
            return VerificationResult("较可信", 80, "来源接近主流媒体、公司公告或新闻线，仍需核对公告原文。")
        if item.url and item.symbols:
            return VerificationResult("需验证", 60, "存在链接和标的映射，但来源权威性不足，需要交叉验证。")
        return VerificationResult("低可信", 40, "信息来源和标的映射不足，不应作为独立投资依据。")
