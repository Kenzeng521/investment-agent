from __future__ import annotations

from pathlib import Path

from loguru import logger


def setup_logging(log_dir: str | Path = "logs") -> None:
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        path / "investment-agent.log",
        rotation="10 MB",
        retention="30 days",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        encoding="utf-8",
    )
    logger.add(lambda msg: print(msg, end=""), level="INFO", colorize=False)
