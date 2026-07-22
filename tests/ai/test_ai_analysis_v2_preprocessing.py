from datetime import datetime, timedelta

from backend.ai.v2.preprocessing import prepare_windows


def chat(buyer_nick: str, when: datetime, content: str, sender: str | None = None):
    return {
        "user_nick": buyer_nick,
        "sender_nick": sender or buyer_nick,
        "msg_time": when,
        "msg_type": "text",
        "content": content,
    }


def test_prepare_windows_masks_identifiers_and_splits_after_24_hours():
    start = datetime(2026, 7, 1, 9)
    rows = [
        chat("buyer", start, "电话18812345678，订单3327506460762954752"),
        chat("buyer", start + timedelta(hours=25, minutes=1), "还没有处理好吗"),
    ]

    windows = prepare_windows("buyer", rows)

    assert len(windows) == 2
    assert "18812345678" not in windows[0].messages[0].content
    assert "3327506460762954752" not in windows[0].messages[0].content
    assert "[手机号]" in windows[0].messages[0].content
    assert "[长编号]" in windows[0].messages[0].content


def test_incremental_window_includes_only_new_messages_plus_20_context_turns():
    start = datetime(2026, 7, 1, 9)
    rows = [
        chat("buyer", start + timedelta(minutes=index), f"历史消息{index}")
        for index in range(25)
    ]
    checkpoint = start + timedelta(minutes=24)
    rows.extend(
        [
            chat("buyer", checkpoint + timedelta(minutes=1), "新增消息1"),
            chat("buyer", checkpoint + timedelta(minutes=2), "新增消息2", sender="客服"),
        ]
    )

    windows = prepare_windows("buyer", rows, checkpoint=checkpoint, context_limit=20)

    assert len(windows) == 1
    assert all(message.msg_time > checkpoint for message in windows[0].new_messages)
    assert len(windows[0].context_messages) == 20
    assert windows[0].new_messages[1].role == "service"


def test_same_messages_have_same_fingerprint_regardless_of_input_order():
    start = datetime(2026, 7, 1, 9)
    rows = [chat("buyer", start, "第一条"), chat("buyer", start + timedelta(minutes=1), "第二条")]

    forward = prepare_windows("buyer", rows)[0]
    reversed_input = prepare_windows("buyer", list(reversed(rows)))[0]

    assert forward.fingerprint == reversed_input.fingerprint
