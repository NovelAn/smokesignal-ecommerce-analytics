#!/usr/bin/env python3
"""Evaluate reviewed V2 cases and write the acceptance report."""

import argparse
from pathlib import Path

from backend.ai.v2.cohort import calculate_acceptance_metrics, render_acceptance_report
from backend.database import Database


SQL_DIR = Path(__file__).parents[1] / "backend/database/sql/ai_analysis_v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/testing/ai-analysis-v2-acceptance-report.md"),
    )
    args = parser.parse_args()

    db = Database()
    rows = db.execute_query(
        (SQL_DIR / "get_acceptance_reviews.sql").read_text(encoding="utf-8")
    )
    audit_rows = db.execute_query(
        (SQL_DIR / "get_acceptance_audit.sql").read_text(encoding="utf-8")
    )
    audit = audit_rows[0] if audit_rows else {}
    metrics = calculate_acceptance_metrics(
        rows,
        failed_result_count=int(audit.get("failed_result_count") or 0),
        duplicate_event_count=int(audit.get("duplicate_event_count") or 0),
    )
    report = render_acceptance_report(metrics)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    return 0 if metrics.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
