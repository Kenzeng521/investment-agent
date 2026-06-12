from notify.wechat_bot import WeChatNotifier


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


def test_serverchan_payload_posts_to_wechat_service(monkeypatch):
    calls = {}

    def fake_post(url, data=None, json=None, timeout=10):
        calls["url"] = url
        calls["data"] = data
        calls["json"] = json
        return FakeResponse({"code": 0})

    monkeypatch.setattr("requests.post", fake_post)
    notifier = WeChatNotifier(provider="serverchan", send_key="send-key")

    assert notifier.send_markdown("# report") is True
    assert calls["url"].endswith("/send-key.send")
    assert calls["data"]["title"] == "开盘前投资决策"
    assert calls["data"]["desp"] == "# report"


def test_pushplus_payload_posts_to_wechat_service(monkeypatch):
    calls = {}

    def fake_post(url, data=None, json=None, timeout=10):
        calls["url"] = url
        calls["json"] = json
        return FakeResponse({"code": 200})

    monkeypatch.setattr("requests.post", fake_post)
    notifier = WeChatNotifier(provider="pushplus", pushplus_token="token")

    assert notifier.send_markdown("# report") is True
    assert calls["url"].endswith("/send")
    assert calls["json"]["token"] == "token"
    assert calls["json"]["template"] == "markdown"
