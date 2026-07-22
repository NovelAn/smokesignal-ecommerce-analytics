from datetime import datetime, timedelta

from backend.ai.v2.rollup import PersistedEvent, PersistedIssue, build_customer_state


NOW = datetime(2026, 7, 22, 12)


def issue(
    code: str,
    *,
    severity: str,
    status: str,
    age_days: int,
) -> PersistedIssue:
    return PersistedIssue(
        issue_category="product",
        issue_code=code,
        issue_detail=code,
        severity=severity,
        status=status,
        last_seen_at=NOW - timedelta(days=age_days),
    )


def event_for(
    item: PersistedIssue,
    *,
    sentiment: str = "Neutral",
    friction: str = "none",
) -> PersistedEvent:
    return PersistedEvent(
        buyer_nick="buyer",
        event_ended_at=item.last_seen_at,
        sentiment_label=sentiment,
        service_friction=friction,
        suggested_action=f"处理{item.issue_code}",
        issues=(item,),
    )


def test_new_open_medium_issue_outweighs_old_resolved_critical_issue():
    old = issue("quality_damage", severity="critical", status="resolved", age_days=200)
    new = issue("material_expectation", severity="medium", status="open", age_days=5)

    state = build_customer_state(events=[event_for(old), event_for(new)], now=NOW)

    assert state.primary_issue_code == new.issue_code
    assert state.recommended_action == "处理material_expectation"


def test_recent_negative_with_high_issue_is_urgent():
    item = issue("quality_damage", severity="high", status="open", age_days=2)

    state = build_customer_state(
        events=[event_for(item, sentiment="Negative")], now=NOW
    )

    assert state.current_sentiment_label == "Negative"
    assert state.attention_priority == "urgent"


def test_recent_negative_without_high_issue_is_high():
    item = issue("material_expectation", severity="low", status="open", age_days=2)

    state = build_customer_state(
        events=[event_for(item, sentiment="Negative")], now=NOW
    )

    assert state.attention_priority == "high"


def test_stale_sentiment_becomes_unknown_after_90_days():
    item = issue("material_expectation", severity="low", status="resolved", age_days=91)

    state = build_customer_state(events=[event_for(item)], now=NOW)

    assert state.current_sentiment_label == "Unknown"
