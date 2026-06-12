from schemas import AccountSnapshot, PortfolioAnalysis
from llm.openai_client import BigModelReportClient


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "# 开盘前投资决策\n\n## 今日执行计划\n\n- 无需操作"}}]}


def test_bigmodel_client_uses_openai_compatible_chat_completions(monkeypatch):
    calls = {}

    def fake_post(url, headers, json, timeout):
        calls["url"] = url
        calls["headers"] = headers
        calls["json"] = json
        calls["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)
    client = BigModelReportClient(api_key="secret", model="glm-4.6v")

    report = client.generate_report(
        snapshot=AccountSnapshot(),
        portfolio=PortfolioAnalysis(
            account_score=80,
            position_score=70,
            sector_concentration_score=70,
            risk_score=80,
        ),
        position_risks=[],
        sector_scores=[],
        news=[],
    )

    assert "bigmodel.cn/api/paas/v4/chat/completions" in calls["url"]
    assert calls["headers"]["Authorization"] == "Bearer secret"
    assert calls["json"]["model"] == "glm-4.6v"
    assert "# 开盘前投资决策" in report
