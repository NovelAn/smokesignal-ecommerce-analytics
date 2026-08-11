#!/usr/bin/env python3
"""Evaluate reviewed V2 cases and write the acceptance report."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.ai.v2.cohort import calculate_acceptance_metrics, render_acceptance_report
from backend.ai.v2.analyzer import AIAnalysisV2Analyzer
from backend.ai.v2.preprocessing import prepare_windows
from backend.ai.v2.repository import AIAnalysisV2Repository
from backend.database import Database


SQL_DIR = Path(__file__).parents[1] / "backend/database/sql/ai_analysis_v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/testing/ai-analysis-v2-acceptance-report.md"),
    )
    parser.add_argument(
        "--recheck-corrected",
        action="store_true",
        help="Re-run corrected cases with the current prompt without persisting results.",
    )
    args = parser.parse_args()

    db = Database()
    rows = db.execute_query(
        (SQL_DIR / "get_acceptance_reviews.sql").read_text(encoding="utf-8")
    )
    rechecked_count = 0
    if args.recheck_corrected:
        rows, rechecked_count = recheck_corrected(rows)
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
    if rechecked_count:
        report = report.replace(
            "Overall:",
            f"Corrected cases rechecked with {AIAnalysisV2Analyzer.PROMPT_VERSION}: **{rechecked_count}**\n\nOverall:",
            1,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    return 0 if metrics.passed else 1


def recheck_corrected(rows: list[dict]) -> tuple[list[dict], int]:
    repository = AIAnalysisV2Repository()
    analyzer = AIAnalysisV2Analyzer(repository=repository)
    updated = []
    count = 0
    for source_row in rows:
        row = dict(source_row)
        if row.get("review_status") == "corrected":
            source = repository.load_source(row["buyer_nick"], "full")
            windows = prepare_windows(
                row["buyer_nick"],
                source.chats,
                prompt_version=analyzer.PROMPT_VERSION,
            )
            window = next(
                window
                for window in windows
                if window.source_from_msg_time <= row["event_started_at"]
                and window.source_to_msg_time >= row["event_ended_at"]
            )
            result = analyzer._analyze_window(window, [], source.profile, None)
            row["model_payload"] = result.payload.model_dump(mode="json")
            count += 1
        updated.append(row)
    return updated, count


if __name__ == "__main__":
    raise SystemExit(main())
