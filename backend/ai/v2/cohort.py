"""Deterministic review sampling and AI Analysis V2 acceptance metrics."""

import json
from dataclasses import dataclass
from typing import Any, Sequence


STRATA = (
    "negative",
    "ambiguity",
    "product_after_sales",
    "operations_friction",
    "baseline",
)


@dataclass(frozen=True)
class Candidate:
    event_id: int
    buyer_nick: str
    stratum: str
    risk_score: float


@dataclass(frozen=True)
class AcceptanceMetrics:
    reviewed_count: int
    evaluable_count: int
    negative_true_positive: int
    negative_predicted: int
    negative_gold: int
    issue_presence_matches: int
    issue_code_matches: int
    resolution_matches: int
    failed_result_count: int
    duplicate_event_count: int

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 1.0

    @property
    def negative_precision(self) -> float:
        return self._ratio(self.negative_true_positive, self.negative_predicted)

    @property
    def negative_recall(self) -> float:
        return self._ratio(self.negative_true_positive, self.negative_gold)

    @property
    def issue_presence_agreement(self) -> float:
        return self._ratio(self.issue_presence_matches, self.evaluable_count)

    @property
    def issue_code_agreement(self) -> float:
        return self._ratio(self.issue_code_matches, self.evaluable_count)

    @property
    def resolution_status_agreement(self) -> float:
        return self._ratio(self.resolution_matches, self.evaluable_count)

    @property
    def passed(self) -> bool:
        return all(
            (
                self.reviewed_count == 50,
                self.evaluable_count == 50,
                self.negative_precision == 1.0,
                self.negative_recall >= 0.9,
                self.issue_presence_agreement >= 0.9,
                self.issue_code_agreement >= 0.8,
                self.resolution_status_agreement >= 0.8,
                self.failed_result_count == 0,
                self.duplicate_event_count == 0,
            )
        )


def select_review_cohort(
    rows: Sequence[Candidate], per_stratum: int = 10
) -> list[Candidate]:
    selected: list[Candidate] = []
    seen: set[str] = set()
    for stratum in STRATA:
        candidates = sorted(
            (row for row in rows if row.stratum == stratum),
            key=lambda row: (-row.risk_score, row.buyer_nick),
        )
        stratum_count = 0
        for candidate in candidates:
            if candidate.buyer_nick in seen:
                continue
            selected.append(candidate)
            seen.add(candidate.buyer_nick)
            stratum_count += 1
            if stratum_count == per_stratum:
                break
        if stratum_count != per_stratum:
            raise ValueError(f"insufficient distinct candidates for {stratum}")
    return selected


def calculate_acceptance_metrics(
    rows: Sequence[dict[str, Any]],
    *,
    failed_result_count: int | None = None,
    duplicate_event_count: int | None = None,
) -> AcceptanceMetrics:
    reviewed = [
        row
        for row in rows
        if row.get("review_status") in {"approved", "corrected"}
    ]
    evaluable: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in reviewed:
        model = _payload(row.get("model_payload"))
        gold = (
            model
            if row["review_status"] == "approved"
            else _payload(row.get("gold_payload"))
        )
        if model and gold:
            evaluable.append((model, gold))

    true_positive = predicted_negative = gold_negative = 0
    issue_presence_matches = issue_code_matches = resolution_matches = 0
    for model, gold in evaluable:
        model_event = model["events"][0]
        gold_event = gold["events"][0]
        model_negative = model_event.get("sentiment_label") == "Negative"
        actual_negative = gold_event.get("sentiment_label") == "Negative"
        predicted_negative += int(model_negative)
        gold_negative += int(actual_negative)
        true_positive += int(model_negative and actual_negative)

        model_codes = {
            issue.get("issue_code") for issue in model_event.get("issues", [])
        }
        gold_codes = {
            issue.get("issue_code") for issue in gold_event.get("issues", [])
        }
        issue_presence_matches += int(bool(model_codes) == bool(gold_codes))
        issue_code_matches += int(model_codes == gold_codes)
        resolution_matches += int(
            model_event.get("resolution_status")
            == gold_event.get("resolution_status")
        )

    return AcceptanceMetrics(
        reviewed_count=len(reviewed),
        evaluable_count=len(evaluable),
        negative_true_positive=true_positive,
        negative_predicted=predicted_negative,
        negative_gold=gold_negative,
        issue_presence_matches=issue_presence_matches,
        issue_code_matches=issue_code_matches,
        resolution_matches=resolution_matches,
        failed_result_count=(
            failed_result_count
            if failed_result_count is not None
            else sum(
                int(row.get("failed_result_persisted") or 0)
                for row in reviewed
            )
        ),
        duplicate_event_count=(
            duplicate_event_count
            if duplicate_event_count is not None
            else sum(
                int(row.get("duplicate_event") or 0) for row in reviewed
            )
        ),
    )


def render_acceptance_report(metrics: AcceptanceMetrics) -> str:
    status = "PASS" if metrics.passed else "FAIL"
    return f"""# AI Analysis V2 Acceptance Report

Overall: **{status}**

| Metric | Result | Threshold |
|---|---:|---:|
| Reviewed cases | {metrics.reviewed_count} / 50 | 50 / 50 |
| Evaluable gold cases | {metrics.evaluable_count} / 50 | 50 / 50 |
| Negative precision | {metrics.negative_true_positive} / {metrics.negative_predicted} ({metrics.negative_precision:.1%}) | 100% |
| Negative recall | {metrics.negative_true_positive} / {metrics.negative_gold} ({metrics.negative_recall:.1%}) | >= 90% |
| Issue presence agreement | {metrics.issue_presence_matches} / {metrics.evaluable_count} ({metrics.issue_presence_agreement:.1%}) | >= 90% |
| issue_code agreement | {metrics.issue_code_matches} / {metrics.evaluable_count} ({metrics.issue_code_agreement:.1%}) | >= 80% |
| resolution_status agreement | {metrics.resolution_matches} / {metrics.evaluable_count} ({metrics.resolution_status_agreement:.1%}) | >= 80% |
| Failed results persisted | {metrics.failed_result_count} | 0 |
| Duplicate events | {metrics.duplicate_event_count} | 0 |
"""


def _payload(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, dict) and value.get("events") else None
