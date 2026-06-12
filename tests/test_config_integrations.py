from pathlib import Path

from config import load_settings


def test_settings_load_bigmodel_moomoo_and_wechat_env(monkeypatch, tmp_path):
    config = tmp_path / "settings.yaml"
    config.write_text(
        """
moomoo:
  enabled: false
  host: 127.0.0.1
  port: 11111
openai:
  model: gpt-5
scheduler:
  timezone: America/New_York
risk:
  auto_trading: false
  require_human_confirm: true
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("MOOMOO_ENABLED", "true")
    monkeypatch.setenv("BIGMODEL_API_KEY", "secret")
    monkeypatch.setenv("BIGMODEL_MODEL", "glm-4.6v")
    monkeypatch.setenv("WECHAT_PROVIDER", "serverchan")
    monkeypatch.setenv("SERVERCHAN_SEND_KEY", "send-key")
    monkeypatch.setenv("MOOMOO_SECURITY_FIRM", "FUTUINC")

    settings = load_settings(Path(config))

    assert settings.moomoo_enabled is True
    assert settings.moomoo_security_firm == "FUTUINC"
    assert settings.bigmodel_api_key == "secret"
    assert settings.bigmodel_model == "glm-4.6v"
    assert settings.wechat_provider == "serverchan"
    assert settings.serverchan_send_key == "send-key"
