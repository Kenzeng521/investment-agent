from __future__ import annotations

import argparse
from pathlib import Path

from loguru import logger

from analysis.portfolio_analyzer import PortfolioAnalyzer
from analysis.event_analyzer import EventAnalyzer
from analysis.risk_engine import RiskEngine
from broker.moomoo_client import MoomooClient
from config import BASE_DIR, load_settings
from data.event_radar import DEFAULT_EVENT_TOPICS, EventRadarFetcher
from data.market_data import MarketDataClient
from data.news_fetcher import NewsFetcher
from data.sector_scanner import DEFAULT_SECTOR_KEYWORDS, SectorScanner
from llm.event_report_client import EventRadarReportClient
from llm.openai_client import OpenAIReportClient
from logging_config import setup_logging
from notify.wechat_bot import WeChatNotifier
from scheduler.market_calendar import MarketCalendar
from schemas import AgentRunResult, EventRadarRunResult


def run(force: bool = False, notify: bool = True) -> AgentRunResult | EventRadarRunResult | None:
    settings = load_settings()
    setup_logging(BASE_DIR / "logs")
    calendar = MarketCalendar(settings.timezone)
    if not force and not calendar.is_trading_day():
        logger.info("Today is not a US trading day; skip run")
        return None
    if not force and not calendar.is_premarket_run_window(
        minutes_before_open=settings.run_minutes_before_open
    ):
        next_run = calendar.next_premarket_run_time(
            minutes_before_open=settings.run_minutes_before_open
        )
        logger.info("Outside pre-market run window; next run at {}", next_run.isoformat())
        return None

    if settings.agent_mode == "event_radar":
        return run_event_radar(settings, notify=notify)

    return run_portfolio_analysis(settings, notify=notify)


def run_event_radar(settings, notify: bool = True) -> EventRadarRunResult:
    logger.info("Starting US equity technology event radar")
    topics = settings.event_topics or DEFAULT_EVENT_TOPICS
    news = EventRadarFetcher().fetch(
        topics=topics,
        symbols=settings.watched_symbols,
        max_items=settings.event_max_items,
    )
    events, candidates = EventAnalyzer(candidate_universe=settings.watched_symbols).analyze(news)
    report = EventRadarReportClient(settings).generate_report(events, candidates)

    output_dir = BASE_DIR / "reports"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "latest.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info("Event radar report written to {}", report_path)

    if notify:
        WeChatNotifier(
            provider=settings.wechat_provider,
            send_key=settings.serverchan_send_key,
            pushplus_token=settings.pushplus_token,
        ).send_markdown(report)

    result = EventRadarRunResult(
        report_markdown=report,
        events=events,
        candidates=candidates,
        metadata={
            "report_path": str(report_path),
            "mode": "event_radar",
            "event_count": len(events),
            "candidate_count": len(candidates),
        },
    )
    logger.info("US equity technology event radar completed")
    return result


def run_portfolio_analysis(settings, notify: bool = True) -> AgentRunResult:
    logger.info("Starting pre-market investment analysis")
    broker = MoomooClient(settings)
    account = broker.get_account_snapshot()
    symbols = [position.symbol for position in account.positions] or settings.watched_symbols

    market_client = MarketDataClient()
    market = market_client.get_market_snapshot(symbols)
    for position in account.positions:
        if position.symbol in market.quotes and market.quotes[position.symbol].price > 0:
            quote = market.quotes[position.symbol]
            position.market_price = quote.price
            position.market_value = round(position.quantity * quote.price, 2)
            position.unrealized_pl = round((quote.price - position.cost_price) * position.quantity, 2)
            position.unrealized_pl_pct = round(((quote.price / position.cost_price) - 1) * 100, 2) if position.cost_price else 0

    topics = list(DEFAULT_SECTOR_KEYWORDS.keys())
    news = NewsFetcher().fetch(symbols=symbols, topics=topics)
    sector_scores = SectorScanner().scan(news, market.sector_performance)
    portfolio = PortfolioAnalyzer().analyze(account)
    position_risks = RiskEngine().analyze_account(account)
    report = OpenAIReportClient(settings).generate_report(account, portfolio, position_risks, sector_scores, news)

    output_dir = BASE_DIR / "reports"
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "latest.md"
    report_path.write_text(report, encoding="utf-8")
    logger.info("Report written to {}", report_path)

    if notify:
        WeChatNotifier(
            provider=settings.wechat_provider,
            send_key=settings.serverchan_send_key,
            pushplus_token=settings.pushplus_token,
        ).send_markdown(report)

    result = AgentRunResult(
        report_markdown=report,
        account=account,
        portfolio=portfolio,
        position_risks=position_risks,
        sector_scores=sector_scores,
        metadata={"report_path": str(report_path), "auto_trading": settings.auto_trading},
    )
    logger.info("Investment analysis run completed")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-market investment analysis agent")
    parser.add_argument("--force", action="store_true", help="Run even if today is not a US trading day")
    parser.add_argument("--no-notify", action="store_true", help="Skip WeChat notification")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(force=args.force, notify=not args.no_notify)
