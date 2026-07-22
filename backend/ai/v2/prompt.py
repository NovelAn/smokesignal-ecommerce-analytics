"""Prompt construction for event and issue analysis."""

import json
from typing import Any, Sequence

from .preprocessing import MessageWindow
from .schemas import AnalysisPayload, ISSUE_TAXONOMY


def build_analysis_prompt(
    window: MessageWindow, open_events: Sequence[dict[str, Any]]
) -> str:
    allowed_ids = [event["id"] for event in open_events]
    allowed = ", ".join(map(str, allowed_ids)) or "无"
    continuation_example = (
        json.dumps(
            {"event_action": "continue_event", "related_event_id": allowed_ids[0]},
            ensure_ascii=False,
        )
        if allowed_ids
        else '{"event_action": "new_event", "related_event_id": null}'
    )
    taxonomy = "\n".join(
        f"- {category}: {', '.join(sorted(codes))}"
        for category, codes in ISSUE_TAXONOMY.items()
    )
    messages = "\n".join(
        f"[{message.msg_time.isoformat()}][{'买家' if message.role == 'buyer' else '客服'}] {message.content}"
        for message in window.messages
    )
    schema = json.dumps(
        AnalysisPayload.model_json_schema(), ensure_ascii=False, indent=2
    )
    open_event_json = json.dumps(list(open_events), ensure_ascii=False)

    return f"""你是电商客服事件与问题分析专家。仅返回符合 JSON Schema 的 JSON 对象。

【事件边界】
- 同一窗口允许输出多个 events，每个 event 允许零个或多个 issues。
- new_event 表示新主题，related_event_id 必须为 null。
- continue_event 仅用于延续下列开放事件，可延续事件 ID：{allowed}。
- 不得引用列表外的 related_event_id。示例：{continuation_example}
- 开放事件：{open_event_json}

【情感边界】
- 情感只判断买家的表达；客服消息只提供语境、解释和处理结果。
- 真伪求证、正常退换货、衣服太薄、发错货、实物与图片不符、解释不清和来回沟通，默认 Neutral，但仍要提取真实 issue。
- 只有明确投诉或升级行动、辱骂威胁、对商家/商品/服务的明确强负面定性才是 Negative。
- “是假货吗”是求证，不是“你们就是卖假货”。多个轻度不满不能累加升级为 Negative。
- Negative 只能使用 explicit_complaint、abuse_or_threat、strong_negative_evaluation；真伪求证使用 authenticity_concern。

【问题分类】
issue_code 必须从下表选择，具体事实写入 issue_detail；不得创造新的 issue_code：
{taxonomy}

【证据】
- evidence_text 只引用经过脱敏的买家原话，不得使用客服话术作为买家情感证据。
- resolution_status 和 customer_accepted 必须根据完整上下文判断，无法确认时用 unknown/null。

【JSON Schema】
{schema}

【对话】
{messages}
"""
