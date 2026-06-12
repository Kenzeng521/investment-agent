from broker.moomoo_client import MoomooClient
from config import Settings


class _FakeSecurityFirm:
    FUTUINC = "FUTUINC"
    FUTUSG = "FUTUSG"
    FUTUSECURITIES = "FUTUSECURITIES"
    FUTUMY = "FUTUMY"
    FUTUJP = "FUTUJP"
    FUTUAU = "FUTUAU"
    FUTUCA = "FUTUCA"


class _FakeFt:
    SecurityFirm = _FakeSecurityFirm


def test_moomoo_client_returns_empty_snapshot_when_opend_unreachable(monkeypatch):
    client = MoomooClient(Settings(moomoo_enabled=True, moomoo_host="127.0.0.1", moomoo_port=1))
    monkeypatch.setattr(client, "_is_opend_reachable", lambda: False)

    snapshot = client.get_account_snapshot()

    assert snapshot.positions == []
    assert snapshot.cash == 0


def test_moomoo_security_firm_uses_configured_value():
    client = MoomooClient(Settings(moomoo_security_firm="FUTUSG"))

    assert client._security_firm_candidates(_FakeFt) == ["FUTUSG"]


def test_moomoo_security_firm_auto_prefers_us_then_global_regions():
    client = MoomooClient(Settings(moomoo_security_firm="AUTO"))

    assert client._security_firm_candidates(_FakeFt) == [
        "FUTUINC",
        "FUTUSG",
        "FUTUSECURITIES",
        "FUTUMY",
        "FUTUJP",
        "FUTUAU",
        "FUTUCA",
    ]


def test_moomoo_account_summary_marks_available_simulate_account():
    import pandas as pd

    client = MoomooClient(Settings())
    data = pd.DataFrame(
        [
            {
                "acc_id": 4924481,
                "trd_env": "SIMULATE",
                "acc_type": "MARGIN",
                "trdmarket_auth": ["US"],
                "acc_status": "ACTIVE",
            }
        ]
    )

    assert client._available_account_summary(data) == "4924481/SIMULATE/MARGIN/[US]/ACTIVE"
