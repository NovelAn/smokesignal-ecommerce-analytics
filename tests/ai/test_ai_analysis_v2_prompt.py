from datetime import datetime

from backend.ai.v2.preprocessing import MessageWindow, PreparedMessage
from backend.ai.v2.prompt import build_analysis_prompt


def window() -> MessageWindow:
    message = PreparedMessage(
        msg_time=datetime(2026, 7, 20, 10),
        role="buyer",
        content="是假货吗",
    )
    return MessageWindow(
        messages=(message,),
        new_messages=(message,),
        context_messages=(),
        fingerprint="abc",
    )


def test_prompt_requires_multiple_issues_and_controlled_codes():
    prompt = build_analysis_prompt(window(), open_events=[])

    assert '"events"' in prompt
    assert '"issues"' in prompt
    assert "不得创造新的 issue_code" in prompt
    assert "多个轻度不满不能累加升级为 Negative" in prompt
    assert "客服消息只提供语境" in prompt
    assert "authenticity_concern" in prompt
    assert "material_expectation" in prompt


def test_prompt_allows_only_supplied_open_event_ids():
    prompt = build_analysis_prompt(
        window(),
        open_events=[{"id": 17, "topic_summary": "真伪咨询"}],
    )

    assert "可延续事件 ID：17" in prompt
    assert '"related_event_id": 17' in prompt
