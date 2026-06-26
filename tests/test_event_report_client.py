import requests

from config import Settings
from llm.event_report_client import EventRadarReportClient, LocalEventRadarRenderer, _strip_markdown_fence
from schemas import EquityCandidate, MarketEvent


def test_local_event_radar_renderer_outputs_required_sections():
    report = LocalEventRadarRenderer().render(
        events=[
            MarketEvent(
                title="Nvidia supplier announces AI data center contract",
                category="AI算力",
                symbols=["NVDA"],
                importance_score=92,
                impact="利好",
            )
        ],
        candidates=[
            EquityCandidate(
                symbol="NVDA",
                sector="AI算力",
                status="重点跟踪",
                score=92,
                event_count=1,
                latest_events=["Nvidia supplier announces AI data center contract"],
            )
        ],
    )

    assert "# 美股科技成长事件雷达" in report
    assert "## 重大事件" in report
    assert "## 候选跟踪池" in report
    assert "不是买入建议" in report


def test_bigmodel_event_report_retries_and_uses_bounded_prompt(monkeypatch):
    calls = {"count": 0, "payloads": []}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "# 美股科技成长事件雷达\n\n日期：2026-06-26"}}]}

    def fake_post(url, headers, json, timeout):
        calls["count"] += 1
        calls["payloads"].append(json)
        if calls["count"] == 1:
            raise requests.Timeout()
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)
    settings = Settings(
        bigmodel_api_key="secret",
        bigmodel_model="glm-4.6v",
        llm_timeout_seconds=12,
        llm_retry_attempts=2,
        llm_max_tokens=1200,
        llm_event_limit=3,
        llm_candidate_limit=2,
    )
    client = EventRadarReportClient(settings)
    events = [
        MarketEvent(title=f"AI data center event {index}", importance_score=90 - index)
        for index in range(10)
    ]
    candidates = [
        EquityCandidate(symbol=f"T{index}", score=90 - index, latest_events=["event"])
        for index in range(5)
    ]

    report = client.generate_report(events, candidates)

    assert calls["count"] == 2
    assert calls["payloads"][0]["max_tokens"] == 1200
    user_prompt = calls["payloads"][0]["messages"][1]["content"]
    assert user_prompt.count("AI data center event") == 3
    assert "T0" in user_prompt
    assert "T1" in user_prompt
    assert "T2" not in user_prompt
    assert "# 美股科技成长事件雷达" in report


def test_strip_markdown_fence_from_llm_response():
    assert _strip_markdown_fence("```markdown\n# 标题\n```") == "# 标题"
