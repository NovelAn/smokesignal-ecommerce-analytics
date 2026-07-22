"""Strict contracts for AI Analysis V2 model output and persisted state."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.ai.analysis_errors import parse_first_json_object


SentimentLabel = Literal["Positive", "Neutral", "Negative"]
SentimentBasis = Literal[
    "positive_expression",
    "neutral_business",
    "authenticity_concern",
    "explicit_complaint",
    "abuse_or_threat",
    "strong_negative_evaluation",
]
EventAction = Literal["new_event", "continue_event"]
IssueSeverity = Literal["low", "medium", "high", "critical"]
IssueStatus = Literal[
    "open", "explained_pending_acceptance", "resolved", "unknown"
]

ISSUE_TAXONOMY = {
    "product": {
        "material_expectation",
        "color_appearance_mismatch",
        "size_fit",
        "quality_damage",
        "packaging",
    },
    "logistics": {
        "shipping_delay",
        "delivery_failure",
        "return_pickup",
        "address_contact",
    },
    "after_sales": {
        "return_request",
        "exchange_request",
        "refund_delay",
        "repair_warranty",
    },
    "pricing_promotion": {
        "price_change",
        "discount_eligibility",
        "price_difference",
    },
    "inventory": {"out_of_stock", "replenishment_wait"},
    "service": {
        "response_slow",
        "explanation_unclear",
        "repeated_communication",
        "service_attitude",
    },
    "trust": {"authenticity_concern", "advertising_mismatch"},
    "usage_care": {"usage_instruction", "care_maintenance"},
    "other": {"other"},
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IssueAnalysis(StrictModel):
    issue_category: str
    issue_code: str
    issue_detail: str = Field(min_length=1, max_length=500)
    severity: IssueSeverity
    owner: Literal["product", "logistics", "service", "customer", "mixed", "unknown"]
    status: IssueStatus
    is_primary: bool
    evidence_text: str = Field(min_length=1, max_length=500)
    evidence_msg_time: datetime | None = None

    @model_validator(mode="after")
    def code_matches_category(self) -> "IssueAnalysis":
        if self.issue_code not in ISSUE_TAXONOMY.get(self.issue_category, set()):
            raise ValueError("issue_code does not belong to issue_category")
        return self


class EventAnalysis(StrictModel):
    event_action: EventAction
    related_event_id: int | None = None
    topic_summary: str = Field(min_length=1, max_length=500)
    event_started_at: datetime
    event_ended_at: datetime
    sentiment_label: SentimentLabel
    sentiment_score: float = Field(ge=0, le=1)
    sentiment_basis: SentimentBasis
    peak_emotion: Literal[
        "calm", "concern", "anxiety", "dissatisfaction", "anger", "gratitude"
    ]
    service_friction: Literal["none", "low", "medium", "high"]
    resolution_status: Literal[
        "unresolved", "explained_pending_acceptance", "resolved", "unknown"
    ]
    customer_accepted: bool | None
    suggested_action: str = Field(max_length=500)
    issues: list[IssueAnalysis] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_boundaries(self) -> "EventAnalysis":
        negative_bases = {
            "explicit_complaint",
            "abuse_or_threat",
            "strong_negative_evaluation",
        }
        if (self.sentiment_basis in negative_bases) != (
            self.sentiment_label == "Negative"
        ):
            raise ValueError("Negative requires an explicit strong-negative basis")
        if self.event_action == "continue_event" and self.related_event_id is None:
            raise ValueError("continue_event requires related_event_id")
        if self.event_action == "new_event" and self.related_event_id is not None:
            raise ValueError("new_event cannot reference an existing event")
        if self.event_ended_at < self.event_started_at:
            raise ValueError("event_ended_at cannot precede event_started_at")
        return self


class AnalysisPayload(StrictModel):
    events: list[EventAnalysis] = Field(min_length=1)


class CustomerState(StrictModel):
    buyer_nick: str = Field(min_length=1, max_length=255)
    current_sentiment_label: Literal["Positive", "Neutral", "Negative", "Unknown"]
    primary_issue_code: str | None = None
    primary_issue_detail: str | None = Field(default=None, max_length=500)
    active_issue_count: int = Field(ge=0)
    highest_severity: IssueSeverity | None = None
    attention_priority: Literal["urgent", "high", "medium", "low"]
    recommended_action: str = Field(max_length=500)
    analyzed_through_msg_time: datetime | None = None
    last_run_id: int | None = None


class ReviewDecision(StrictModel):
    review_status: Literal["pending", "approved", "corrected", "rejected"]
    gold_payload: AnalysisPayload | None = None
    review_note: str | None = None
    reviewed_by: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def correction_requires_gold_payload(self) -> "ReviewDecision":
        if self.review_status == "corrected" and self.gold_payload is None:
            raise ValueError("corrected review requires gold_payload")
        return self


def validate_model_payload(text: str) -> AnalysisPayload:
    """Extract and validate the first JSON object returned by a model."""
    return AnalysisPayload.model_validate(parse_first_json_object(text))
