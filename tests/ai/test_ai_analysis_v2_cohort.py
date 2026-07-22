from collections import Counter

from backend.ai.v2.cohort import (
    Candidate,
    calculate_acceptance_metrics,
    render_acceptance_report,
    select_review_cohort,
)


STRATA = (
    "negative",
    "ambiguity",
    "product_after_sales",
    "operations_friction",
    "baseline",
)


def candidate_rows():
    return [
        Candidate(
            event_id=index * 100 + rank,
            buyer_nick=f"{stratum}-{rank}",
            stratum=stratum,
            risk_score=100 - rank,
        )
        for index, stratum in enumerate(STRATA)
        for rank in range(12)
    ]


def payload(sentiment="Neutral", issue_code="material_expectation", resolution="resolved"):
    return {
        "events": [
            {
                "sentiment_label": sentiment,
                "resolution_status": resolution,
                "issues": [] if issue_code is None else [{"issue_code": issue_code}],
            }
        ]
    }


def review_rows():
    return [
        {
            "review_status": "approved",
            "model_payload": payload(sentiment="Negative" if index < 10 else "Neutral"),
            "gold_payload": None,
            "failed_result_persisted": 0,
            "duplicate_event": 0,
        }
        for index in range(50)
    ]


def test_cohort_has_five_strata_and_50_distinct_buyers():
    cohort = select_review_cohort(candidate_rows())

    assert len(cohort) == 50
    assert len({case.buyer_nick for case in cohort}) == 50
    assert Counter(case.stratum for case in cohort) == Counter({stratum: 10 for stratum in STRATA})


def test_acceptance_metrics_use_reviewed_gold_only():
    rows = review_rows() + [
        {
            "review_status": "pending",
            "model_payload": payload("Negative"),
            "gold_payload": None,
            "failed_result_persisted": 1,
            "duplicate_event": 1,
        }
    ]

    metrics = calculate_acceptance_metrics(rows)

    assert metrics.reviewed_count == 50
    assert metrics.evaluable_count == 50
    assert metrics.negative_precision == 1
    assert metrics.failed_result_count == 0
    assert metrics.duplicate_event_count == 0
    assert metrics.passed


def test_corrected_gold_changes_negative_precision():
    rows = review_rows()
    rows[0] = {
        **rows[0],
        "review_status": "corrected",
        "gold_payload": payload("Neutral"),
    }

    metrics = calculate_acceptance_metrics(rows)

    assert metrics.negative_precision == 0.9
    assert not metrics.passed


def test_report_contains_exact_metric_fractions():
    report = render_acceptance_report(calculate_acceptance_metrics(review_rows()))

    assert "50 / 50" in report
    assert "Negative precision" in report
    assert "10 / 10" in report


def test_global_failure_audit_is_not_hidden_by_pending_review_rows():
    metrics = calculate_acceptance_metrics(
        review_rows(), failed_result_count=1, duplicate_event_count=0
    )

    assert metrics.failed_result_count == 1
    assert not metrics.passed
