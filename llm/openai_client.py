from __future__ import annotations

from datetime import date
from typing import Iterable, List

import requests
from loguru import logger

from config import Settings
from schemas import AccountSnapshot, NewsItem, PortfolioAnalysis, PositionRisk, SectorScore


def _json(model) -> str:
    if hasattr(model, "model_dump_json"):
        return model.model_dump_json(indent=2)
    return model.json(indent=2, ensure_ascii=False)


def _dict(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class LocalReportRenderer:
    def render(
        self,
        snapshot: AccountSnapshot,
        portfolio: PortfolioAnalysis,
        position_risks: Iterable[PositionRisk],
        sector_scores: Iterable[SectorScore],
        opportunities: List[str] | None = None,
    ) -> str:
        opportunities = opportunities or []
        risks = list(position_risks)
        sectors = sorted(list(sector_scores), key=lambda item: item.total_score, reverse=True)
        lines = [
            "# 开盘前投资决策",
            "",
            f"日期：{date.today().isoformat()}",
            "",
            "## 账户健康度",
            "",
            f"评分：{portfolio.account_score}",
            "",
            f"- 仓位评分：{portfolio.position_score}",
            f"- 行业集中度评分：{portfolio.sector_concentration_score}",
            f"- 风险评分：{portfolio.risk_score}",
            f"- 组合摘要：{portfolio.summary}",
            "",
            "## 当前持仓",
            "",
        ]
        if not risks:
            lines.append("未读取到当前持仓。")
        for risk in risks:
            lines.extend(
                [
                    f"### {risk.symbol}",
                    "",
                    f"- 当前价格：{risk.current_price:.2f}",
                    f"- 成本价：{risk.cost_price:.2f}",
                    f"- 当前盈亏：{risk.pnl_pct:.2f}%",
                    "- 投资逻辑变化：未发现需要立即改变原投资逻辑的信号，继续以风控线管理。",
                    f"- 风险等级：{risk.risk_level}",
                    f"- 止损位：{risk.stop_loss:.2f}",
                    f"- 第一止盈位：{risk.take_profit_1:.2f}",
                    f"- 第二止盈位：{risk.take_profit_2:.2f}",
                    "- 当前评级：持有观察",
                    "- 操作建议：无需操作",
                    "",
                ]
            )
        lines.extend(["## 行业分析", ""])
        for sector in sectors:
            lines.append(
                f"- {sector.name}：综合评分 {sector.total_score}，热度 {sector.heat_score}，"
                f"资金流 {sector.capital_flow_score}，成长性 {sector.growth_score}。{sector.rationale}"
            )
        lines.extend(["", "## 今日新增机会", ""])
        if opportunities:
            lines.extend([f"- {item}" for item in opportunities])
        else:
            lines.append("无新增机会。")
            lines.append("")
            lines.append("今日无新增建仓机会。")
        lines.extend(
            [
                "",
                "## 风险提示",
                "",
                "- 开盘前流动性和隔夜消息可能导致价格跳空，止损位应结合开盘成交确认。",
                "- 若单一行业权重过高，应优先控制回撤而非追求短期收益。",
                "- 本报告为辅助分析，不构成确定性收益承诺。",
                "",
                "## 今日执行计划",
                "",
                "- 无需操作",
                "- 建议价格区间：按开盘后 15-30 分钟有效成交区间观察",
                "- 建议仓位比例：维持当前仓位",
            ]
        )
        return "\n".join(lines)


class OpenAIReportClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fallback_renderer = LocalReportRenderer()
        self.bigmodel_client = BigModelReportClient(
            api_key=settings.bigmodel_api_key,
            model=settings.bigmodel_model,
            fallback_renderer=self.fallback_renderer,
        )

    def generate_report(
        self,
        snapshot: AccountSnapshot,
        portfolio: PortfolioAnalysis,
        position_risks: List[PositionRisk],
        sector_scores: List[SectorScore],
        news: List[NewsItem],
    ) -> str:
        if not self.settings.openai_api_key:
            if self.settings.bigmodel_api_key:
                logger.warning("OPENAI_API_KEY is empty; using BigModel {}", self.settings.bigmodel_model)
                return self.bigmodel_client.generate_report(snapshot, portfolio, position_risks, sector_scores, news)
            logger.warning("OPENAI_API_KEY and BIGMODEL_API_KEY are empty; using local deterministic report renderer")
            return self.fallback_renderer.render(snapshot, portfolio, position_risks, sector_scores)

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            prompt = self._build_prompt(snapshot, portfolio, position_risks, sector_scores, news)
            response = client.responses.create(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "你是谨慎的美股组合风控投资分析师。首要目标是管理当前组合，"
                            "避免频繁交易，保护本金。仅输出 Markdown。"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            text = getattr(response, "output_text", "") or ""
            return text.strip() or self.fallback_renderer.render(snapshot, portfolio, position_risks, sector_scores)
        except Exception as exc:
            if self.settings.bigmodel_api_key:
                logger.exception("OpenAI Responses API call failed; falling back to BigModel: {}", exc)
                return self.bigmodel_client.generate_report(snapshot, portfolio, position_risks, sector_scores, news)
            logger.exception("OpenAI Responses API call failed; using fallback renderer: {}", exc)
            return self.fallback_renderer.render(snapshot, portfolio, position_risks, sector_scores)

    def _build_prompt(
        self,
        snapshot: AccountSnapshot,
        portfolio: PortfolioAnalysis,
        position_risks: List[PositionRisk],
        sector_scores: List[SectorScore],
        news: List[NewsItem],
    ) -> str:
        return f"""
请基于以下数据生成中文 Markdown 投资报告。

硬性原则：
- 首要任务是管理当前组合，不是每天推荐新股票。
- 避免频繁交易，避免追涨杀跌。
- 优先控制回撤，优先保护本金。
- 如果当前组合合理，明确输出“今日无需操作”。
- 若没有明显优于当前持仓的机会，输出“今日无新增建仓机会”。
- 今日执行计划仅允许：无需操作、买入 XXX、加仓 XXX、减仓 XXX、卖出 XXX。
- 必须给出建议价格区间和建议仓位比例。

账户：
{_json(snapshot)}

组合分析：
{_json(portfolio)}

逐仓位风控：
{[_dict(item) for item in position_risks]}

行业评分：
{[_dict(item) for item in sector_scores]}

新闻摘要：
{[_dict(item) for item in news[:30]]}

输出格式必须包含：
# 开盘前投资决策
日期：
## 账户健康度
## 当前持仓
## 行业分析
## 今日新增机会
## 风险提示
## 今日执行计划
"""


class BigModelReportClient:
    def __init__(
        self,
        api_key: str,
        model: str = "glm-4.6v",
        base_url: str = "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        timeout_seconds: int = 60,
        fallback_renderer: LocalReportRenderer | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.fallback_renderer = fallback_renderer or LocalReportRenderer()

    def generate_report(
        self,
        snapshot: AccountSnapshot,
        portfolio: PortfolioAnalysis,
        position_risks: List[PositionRisk],
        sector_scores: List[SectorScore],
        news: List[NewsItem],
    ) -> str:
        if not self.api_key:
            logger.warning("BIGMODEL_API_KEY is empty; using local deterministic report renderer")
            return self.fallback_renderer.render(snapshot, portfolio, position_risks, sector_scores)
        prompt = OpenAIReportClient._build_prompt(
            self, snapshot, portfolio, position_risks, sector_scores, news
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是谨慎的美股组合风控投资分析师。首要目标是管理当前组合，"
                        "避免频繁交易，保护本金。仅输出 Markdown。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip() or self.fallback_renderer.render(
                snapshot, portfolio, position_risks, sector_scores
            )
        except Exception as exc:
            logger.warning("BigModel API call failed; using fallback renderer: {}", exc.__class__.__name__)
            return self.fallback_renderer.render(snapshot, portfolio, position_risks, sector_scores)
