from notify.wechat_bot import WeComMarkdownMessage


def test_wecom_markdown_payload_shape():
    payload = WeComMarkdownMessage(content="# 开盘前投资决策").to_payload()

    assert payload == {
        "msgtype": "markdown",
        "markdown": {"content": "# 开盘前投资决策"},
    }
