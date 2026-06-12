from __future__ import annotations

from dataclasses import dataclass

import requests
from loguru import logger


@dataclass(frozen=True)
class WeComMarkdownMessage:
    content: str

    def to_payload(self) -> dict:
        return {"msgtype": "markdown", "markdown": {"content": self.content}}


class WeChatBot:
    def __init__(self, webhook_url: str, timeout_seconds: int = 10):
        self.webhook_url = webhook_url
        self.timeout_seconds = timeout_seconds

    def send_markdown(self, content: str) -> bool:
        if not self.webhook_url:
            logger.warning("WECHAT_WEBHOOK_URL is empty; skip WeCom notification")
            return False
        payload = WeComMarkdownMessage(content=content).to_payload()
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            body = response.json()
            ok = body.get("errcode") == 0
            if not ok:
                logger.error("WeCom notification failed: {}", body)
            return ok
        except Exception as exc:
            logger.exception("Failed to send WeCom notification: {}", exc)
            return False


class WeChatNotifier:
    """Personal WeChat notification via service-account push providers."""

    def __init__(
        self,
        provider: str = "serverchan",
        send_key: str = "",
        pushplus_token: str = "",
        timeout_seconds: int = 10,
    ):
        self.provider = provider.lower().strip()
        self.send_key = send_key
        self.pushplus_token = pushplus_token
        self.timeout_seconds = timeout_seconds

    def send_markdown(self, content: str) -> bool:
        if self.provider == "serverchan":
            return self._send_serverchan(content)
        if self.provider == "pushplus":
            return self._send_pushplus(content)
        logger.error("Unsupported WECHAT_PROVIDER: {}", self.provider)
        return False

    def _send_serverchan(self, content: str) -> bool:
        if not self.send_key:
            logger.warning("SERVERCHAN_SEND_KEY is empty; skip WeChat notification")
            return False
        url = f"https://sctapi.ftqq.com/{self.send_key}.send"
        try:
            response = requests.post(
                url,
                data={"title": "开盘前投资决策", "desp": content},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            ok = body.get("code") == 0
            if not ok:
                logger.error("ServerChan notification failed: {}", body)
            else:
                logger.info("ServerChan notification accepted")
            return ok
        except Exception as exc:
            logger.exception("Failed to send ServerChan notification: {}", exc)
            return False

    def _send_pushplus(self, content: str) -> bool:
        if not self.pushplus_token:
            logger.warning("PUSHPLUS_TOKEN is empty; skip WeChat notification")
            return False
        try:
            response = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": self.pushplus_token,
                    "title": "开盘前投资决策",
                    "content": content,
                    "template": "markdown",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            ok = body.get("code") == 200
            if not ok:
                logger.error("PushPlus notification failed: {}", body)
            return ok
        except Exception as exc:
            logger.exception("Failed to send PushPlus notification: {}", exc)
            return False
