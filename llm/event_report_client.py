from __future__ import annotations

from datetime import date
from time import sleep
from typing import List

import requests
from loguru import logger

from config import Settings
from schemas import EquityCandidate, MarketEvent
from macro_market_intelligence_engine import MacroMarketIntelligenceReport


def _dump_items(items) -> list[dict]:
    result = []
    for item in items:
        if hasattr(item, "model_dump"):
            result.append(item.model_dump())
        else:
            result.append(item.dict())
    return result


def _strip_markdown_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```markdown"):
        stripped = stripped[len("```markdown") :].strip()
    elif stripped.startswith("```"):
        stripped = stripped[3:].strip()
    if stripped.endswith("```"):
        stripped = stripped[:-3].strip()
    return stripped


class LocalEventRadarRenderer:
    def render(self, events: List[MarketEvent], candidates: List[EquityCandidate]) -> str:
        top_events = sorted(events, key=lambda item: item.importance_score, reverse=True)[:12]
        top_candidates = sorted(candidates, key=lambda item: item.score, reverse=True)[:10]
        ipo_events = [event for event in top_events if event.category == "IPO"]
        lines = [
            "# 美股科技成长事件雷达",
            "",
            f"日期：{date.today().isoformat()}",
            "",
            "## 今日结论",
            "",
            "本报告聚焦 AI、半导体、云计算、数据中心、电力、核能、机器人、自动驾驶、网络安全及 IPO 事件。候选跟踪池仅用于后续研究优先级排序，不是买入建议。",
            "",
            "## 重大事件",
            "",
        ]
        if not top_events:
            lines.append("未抓取到足够高质量的重大事件，今日以观察为主。")
        for event in top_events:
            symbols = ", ".join(event.symbols) if event.symbols else "未映射"
            lines.append(
                f"- **[{event.category}] {event.title}**：评分 {event.importance_score}，影响 {event.impact}，可信度 {event.verification_status}，相关标的 {symbols}。{event.rationale}"
            )
        lines.extend(["", "## 候选跟踪池", ""])
        if not top_candidates:
            lines.append("今日无足够明确的候选跟踪标的。")
        for candidate in top_candidates:
            display_name = f"{candidate.symbol} / {candidate.name}" if candidate.name else candidate.symbol
            latest = "；".join(candidate.latest_events[:2])
            lines.append(
                f"- **{display_name}**（{candidate.sector}）：{candidate.status}，评分 {candidate.score}，事件数 {candidate.event_count}。{latest}"
            )
        lines.extend(["", "## IPO / 新上市", ""])
        if ipo_events:
            for event in ipo_events:
                lines.append(f"- {event.title}")
        else:
            lines.append("今日未发现高优先级 IPO / 新上市事件。")
        lines.extend(
            [
                "",
                "## 风险与噪音过滤",
                "",
                "- 新闻热度不等于基本面改善；重点验证订单、收入、利润率、现金流和估值。",
                "- 候选跟踪池不是买入建议，不输出自动交易指令。",
                "- 对单日上涨后的主题股，优先检查估值和预期拥挤风险。",
                "",
                "## 今日关注清单",
                "",
                "- 跟踪高分事件是否被公司公告、SEC 文件或财报电话会验证。",
                "- 对候选标的补充估值、流动性和下行风险分析后再进入投资研究。",
            ]
        )
        return "\n".join(lines)


class EventRadarReportClient:
    def __init__(
        self,
        settings: Settings,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        timeout_seconds: int | None = None,
    ):
        self.settings = settings
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self.fallback_renderer = LocalEventRadarRenderer()

    def generate_report(self, events: List[MarketEvent], candidates: List[EquityCandidate]) -> str:
        if self.settings.openai_api_key:
            return self._generate_with_openai(events, candidates)
        if self.settings.bigmodel_api_key:
            return self._generate_with_bigmodel(events, candidates)
        return self.fallback_renderer.render(events, candidates)

    def _generate_with_openai(self, events: List[MarketEvent], candidates: List[EquityCandidate]) -> str:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._build_prompt(events, candidates)},
                ],
            )
            text = getattr(response, "output_text", "") or ""
            return text.strip() or self.fallback_renderer.render(events, candidates)
        except Exception as exc:
            logger.exception("OpenAI event radar report failed: {}", exc)
            if self.settings.bigmodel_api_key:
                return self._generate_with_bigmodel(events, candidates)
            return self.fallback_renderer.render(events, candidates)

    def _generate_with_bigmodel(self, events: List[MarketEvent], candidates: List[EquityCandidate]) -> str:
        prompt_events = events[: self.settings.llm_event_limit]
        prompt_candidates = candidates[: self.settings.llm_candidate_limit]
        payload = {
            "model": self.settings.bigmodel_model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._build_prompt(prompt_events, prompt_candidates)},
            ],
            "temperature": 0.2,
            "max_tokens": self.settings.llm_max_tokens,
        }
        attempts = max(1, self.settings.llm_retry_attempts)
        for attempt in range(1, attempts + 1):
            try:
                response = requests.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.settings.bigmodel_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                body = response.json()
                content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content.strip():
                    if attempt > 1:
                        logger.info("BigModel event radar report succeeded on retry {}", attempt)
                    return _strip_markdown_fence(content)
            except Exception as exc:
                logger.warning(
                    "BigModel event radar report attempt {}/{} failed: {}",
                    attempt,
                    attempts,
                    exc.__class__.__name__,
                )
                if attempt < attempts:
                    sleep(min(attempt, 3))
        logger.warning("Using local event radar renderer after BigModel failures")
        return self.fallback_renderer.render(events, candidates)

    def _system_prompt(self) -> str:
        return (
            "你是美股科技成长股事件雷达分析师。输出中文 Markdown。"
            "你的任务是筛选重大公开事件和研究候选，而不是给出买入建议。"
            "必须区分事实、推断和需要继续验证的地方。"
        )

    def _build_prompt(self, events: List[MarketEvent], candidates: List[EquityCandidate]) -> str:
        report_date = date.today().isoformat()
        return f"""
请生成每日美股科技成长事件雷达报告。

硬性要求：
- 日期必须写为：{report_date}。
- 输出控制在 900 字以内，语言稳定、克制、适合每日微信推送。
- 聚焦 AI、半导体、云计算、数据中心、电力、核能、机器人、自动驾驶、网络安全、IPO。
- 输出重大事件和候选跟踪池。
- 候选跟踪池只是研究优先级，不是买入建议。
- 不允许输出自动交易指令。
- 对每个候选说明为什么值得跟踪、第一拒绝理由、下一步验证事项。
- 只能依据下面的事件和候选数据写报告；不得添加列表中没有的公司、数字、财务数据、IPO 状态或传闻。
- 不要把 ticker 对应到错误公司；候选数据里有 name 时使用该名称，没有 name 时只写 ticker。
- 对 RSS 标题来源不够权威、信息不足或无法验证的内容，标注“需验证”，不要扩写成确定事实。
- 涉及 IPO、并购、监管、业绩和订单时，优先写“标题显示/报道提到”，除非事件标题本身来自公司公告或 SEC 文件。

事件：
{_dump_items(events)}

候选：
{_dump_items(candidates)}

输出格式：
# 美股科技成长事件雷达
日期：{report_date}
## 今日结论
## 重大事件
## 科技成长主题
## 候选跟踪池
## IPO / 新上市
## 风险与噪音过滤
## 今日关注清单
"""


def merge_macro_and_event_reports(
    macro_report: MacroMarketIntelligenceReport | None, event_report: str
) -> str:
    if not macro_report:
        return event_report
    return "\n\n".join(
        [
            "# 开盘前市场资金状态与科技事件雷达",
            "## Macro Market Intelligence",
            macro_report.to_wechat_text(),
            "## Technology Event Radar",
            event_report,
        ]
    )
