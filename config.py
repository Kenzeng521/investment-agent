from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


BASE_DIR = Path(__file__).resolve().parent


def load_env_file(path: Path | None = None) -> None:
    env_path = path or BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "investment-agent"
    agent_mode: str = "event_radar"
    timezone: str = "America/New_York"
    run_minutes_before_open: int = 30
    auto_trading: bool = False
    require_human_confirm: bool = True
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    bigmodel_api_key: str = ""
    bigmodel_model: str = "glm-4.6v"
    llm_timeout_seconds: int = 45
    llm_retry_attempts: int = 2
    llm_max_tokens: int = 1600
    llm_event_limit: int = 18
    llm_candidate_limit: int = 10
    wechat_webhook_url: str = ""
    wechat_provider: str = "serverchan"
    serverchan_send_key: str = ""
    pushplus_token: str = ""
    moomoo_host: str = "127.0.0.1"
    moomoo_port: int = 11111
    moomoo_trade_env: str = "REAL"
    moomoo_market: str = "US"
    moomoo_security_firm: str = "AUTO"
    moomoo_enabled: bool = False
    watched_symbols: List[str] = field(default_factory=list)
    sectors: Dict[str, List[str]] = field(default_factory=dict)
    event_topics: Dict[str, str] = field(default_factory=dict)
    event_max_items: int = 80
    raw: Dict[str, Any] = field(default_factory=dict)


def load_settings(config_path: Path | None = None) -> Settings:
    load_env_file()
    path = config_path or BASE_DIR / "settings.yaml"
    raw: Dict[str, Any] = {}
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    moomoo = raw.get("moomoo", {})
    openai = raw.get("openai", {})
    llm = raw.get("llm", {})
    scheduler = raw.get("scheduler", {})
    risk = raw.get("risk", {})

    return Settings(
        app_name=raw.get("app_name", "investment-agent"),
        agent_mode=os.getenv("AGENT_MODE", raw.get("agent", {}).get("mode", "event_radar")),
        timezone=scheduler.get("timezone", os.getenv("TIMEZONE", "America/New_York")),
        run_minutes_before_open=int(scheduler.get("run_minutes_before_open", 30)),
        auto_trading=_env_bool("AUTO_TRADING", bool(risk.get("auto_trading", False))),
        require_human_confirm=_env_bool(
            "REQUIRE_HUMAN_CONFIRM", bool(risk.get("require_human_confirm", True))
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", openai.get("model", "gpt-5")),
        bigmodel_api_key=os.getenv("BIGMODEL_API_KEY", ""),
        bigmodel_model=os.getenv("BIGMODEL_MODEL", raw.get("bigmodel", {}).get("model", "glm-4.6v")),
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", llm.get("timeout_seconds", 45))),
        llm_retry_attempts=int(os.getenv("LLM_RETRY_ATTEMPTS", llm.get("retry_attempts", 2))),
        llm_max_tokens=int(os.getenv("LLM_MAX_TOKENS", llm.get("max_tokens", 1600))),
        llm_event_limit=int(os.getenv("LLM_EVENT_LIMIT", llm.get("event_limit", 18))),
        llm_candidate_limit=int(os.getenv("LLM_CANDIDATE_LIMIT", llm.get("candidate_limit", 10))),
        wechat_webhook_url=os.getenv("WECHAT_WEBHOOK_URL", ""),
        wechat_provider=os.getenv("WECHAT_PROVIDER", raw.get("wechat", {}).get("provider", "serverchan")),
        serverchan_send_key=os.getenv("SERVERCHAN_SEND_KEY", ""),
        pushplus_token=os.getenv("PUSHPLUS_TOKEN", ""),
        moomoo_host=os.getenv("MOOMOO_HOST", moomoo.get("host", "127.0.0.1")),
        moomoo_port=int(os.getenv("MOOMOO_PORT", moomoo.get("port", 11111))),
        moomoo_trade_env=os.getenv("MOOMOO_TRADE_ENV", moomoo.get("trade_env", "REAL")),
        moomoo_market=os.getenv("MOOMOO_MARKET", moomoo.get("market", "US")),
        moomoo_security_firm=os.getenv(
            "MOOMOO_SECURITY_FIRM", moomoo.get("security_firm", "AUTO")
        ),
        moomoo_enabled=_env_bool("MOOMOO_ENABLED", bool(moomoo.get("enabled", False))),
        watched_symbols=raw.get("watched_symbols", []),
        sectors=raw.get("sectors", {}),
        event_topics=raw.get("event_radar", {}).get("topics", {}),
        event_max_items=int(os.getenv("EVENT_MAX_ITEMS", raw.get("event_radar", {}).get("max_items", 80))),
        raw=raw,
    )
