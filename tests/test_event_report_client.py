from llm.event_report_client import LocalEventRadarRenderer
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
