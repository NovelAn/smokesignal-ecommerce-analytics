"""Current-state rollup from persisted AI Analysis V2 events."""

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from .schemas import CustomerState


SEVERITY_FACTOR = {"low": 1, "medium": 2, "high": 3, "critical": 4}
STATUS_FACTOR = {
    "open": 1.0,
    "explained_pending_acceptance": 0.7,
    "unknown": 0.5,
    "resolved": 0.15,
}


@dataclass(frozen=True)
class PersistedIssue:
    issue_category: str
    issue_code: str
    issue_detail: str
    severity: str
    status: str
    last_seen_at: datetime


@dataclass(frozen=True)
class PersistedEvent:
    buyer_nick: str
    event_ended_at: datetime
    sentiment_label: str
    service_friction: str
    suggested_action: str
    issues: tuple[PersistedIssue, ...]
    event_id: int | None = None


def recency_factor(age_days: int) -> float:
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.6
    if age_days <= 180:
        return 0.3
    return 0.1


def issue_weight(issue: PersistedIssue, now: datetime) -> float:
    age_days = max(0, (now - issue.last_seen_at).days)
    return (
        SEVERITY_FACTOR[issue.severity]
        * STATUS_FACTOR[issue.status]
        * recency_factor(age_days)
    )


def build_customer_state(
    events: Sequence[PersistedEvent],
    now: datetime,
    *,
    buyer_nick: str | None = None,
    last_run_id: int | None = None,
) -> CustomerState:
    ordered = sorted(events, key=lambda event: event.event_ended_at)
    resolved_buyer = buyer_nick or (ordered[-1].buyer_nick if ordered else "unknown")
    recent_events = [
        event for event in ordered if (now - event.event_ended_at).days <= 90
    ]
    current_sentiment = (
        recent_events[-1].sentiment_label if recent_events else "Unknown"
    )

    issue_events = [
        (issue, event)
        for event in ordered
        for issue in event.issues
    ]
    primary_pair = max(
        issue_events,
        key=lambda pair: (issue_weight(pair[0], now), pair[0].last_seen_at),
        default=None,
    )
    active = [issue for issue, _ in issue_events if issue.status != "resolved"]
    highest_severity = (
        max(active, key=lambda issue: SEVERITY_FACTOR[issue.severity]).severity
        if active
        else None
    )
    has_high_issue = any(
        issue.severity in {"high", "critical"} for issue in active
    )
    has_medium_issue = any(issue.severity == "medium" for issue in active)
    high_friction = any(
        event.service_friction == "high" for event in recent_events
    )
    if current_sentiment == "Negative" and has_high_issue:
        priority = "urgent"
    elif current_sentiment == "Negative" or has_high_issue:
        priority = "high"
    elif has_medium_issue or high_friction:
        priority = "medium"
    else:
        priority = "low"

    primary_issue, primary_event = primary_pair or (None, None)
    return CustomerState(
        buyer_nick=resolved_buyer,
        current_sentiment_label=current_sentiment,
        primary_issue_code=primary_issue.issue_code if primary_issue else None,
        primary_issue_detail=primary_issue.issue_detail if primary_issue else None,
        active_issue_count=len(active),
        highest_severity=highest_severity,
        attention_priority=priority,
        recommended_action=primary_event.suggested_action if primary_event else "",
        analyzed_through_msg_time=ordered[-1].event_ended_at if ordered else None,
        last_run_id=last_run_id,
    )
