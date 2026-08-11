import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.ai.v2.schemas import (
    AnalysisPayload,
    CustomerState,
    ReviewDecision,
    validate_model_payload,
)


def valid_payload() -> dict:
    return {
        "events": [
            {
                "event_action": "new_event",
                "related_event_id": None,
                "topic_summary": "客户反馈商品颜色与图片有差异",
                "event_started_at": "2026-07-20T10:00:00",
                "event_ended_at": "2026-07-20T10:05:00",
                "sentiment_label": "Neutral",
                "sentiment_score": 0.45,
                "sentiment_basis": "neutral_business",
                "peak_emotion": "concern",
                "service_friction": "none",
                "resolution_status": "explained_pending_acceptance",
                "customer_accepted": None,
                "suggested_action": "确认客户是否接受色差说明",
                "issues": [
                    {
                        "issue_category": "product",
                        "issue_code": "color_appearance_mismatch",
                        "issue_detail": "实物颜色与商品图片观感不一致",
                        "severity": "medium",
                        "owner": "product",
                        "status": "explained_pending_acceptance",
                        "is_primary": True,
                        "evidence_text": "颜色和图片不一样",
                        "evidence_msg_time": "2026-07-20T10:00:00",
                    }
                ],
            }
        ]
    }


def second_issue() -> dict:
    issue = deepcopy(valid_payload()["events"][0]["issues"][0])
    issue.update(
        issue_category="service",
        issue_code="explanation_unclear",
        issue_detail="客户尚未理解客服解释",
        owner="service",
        is_primary=False,
        evidence_text="还是没听懂",
    )
    return issue


def test_analysis_payload_accepts_multiple_issues():
    payload = valid_payload()
    payload["events"][0]["issues"].append(second_issue())

    result = AnalysisPayload.model_validate(payload)

    assert len(result.events[0].issues) == 2


def test_analysis_payload_rejects_unknown_issue_code():
    payload = valid_payload()
    payload["events"][0]["issues"][0]["issue_code"] = "invented_code"

    with pytest.raises(ValidationError):
        AnalysisPayload.model_validate(payload)


def test_negative_requires_negative_basis():
    payload = valid_payload()
    payload["events"][0].update(
        sentiment_label="Negative",
        sentiment_basis="authenticity_concern",
    )

    with pytest.raises(ValidationError):
        AnalysisPayload.model_validate(payload)


def test_continue_event_requires_related_event_id():
    payload = valid_payload()
    payload["events"][0]["event_action"] = "continue_event"

    with pytest.raises(ValidationError):
        AnalysisPayload.model_validate(payload)


def test_model_response_parser_reuses_first_json_object_extraction():
    result = validate_model_payload(f"模型分析如下：\n{json.dumps(valid_payload(), ensure_ascii=False)}")

    assert result.events[0].issues[0].issue_code == "color_appearance_mismatch"


def test_model_response_parser_accepts_one_strict_event_without_outer_wrapper():
    event = valid_payload()["events"][0]

    result = validate_model_payload(json.dumps(event, ensure_ascii=False))

    assert result.events[0].topic_summary == event["topic_summary"]


def test_customer_state_and_review_decision_contracts():
    state = CustomerState.model_validate(
        {
            "buyer_nick": "buyer",
            "current_sentiment_label": "Unknown",
            "primary_issue_code": None,
            "primary_issue_detail": None,
            "active_issue_count": 0,
            "highest_severity": None,
            "attention_priority": "low",
            "recommended_action": "",
            "analyzed_through_msg_time": None,
            "last_run_id": None,
        }
    )
    review = ReviewDecision.model_validate({"review_status": "approved"})

    assert state.current_sentiment_label == "Unknown"
    assert review.gold_payload is None


def test_corrected_review_requires_gold_payload():
    with pytest.raises(ValidationError):
        ReviewDecision.model_validate({"review_status": "corrected"})
