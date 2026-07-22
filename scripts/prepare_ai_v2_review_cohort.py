#!/usr/bin/env python3
"""Preview or write the deterministic 50-case AI Analysis V2 review cohort."""

import argparse
import json
from collections import Counter
from pathlib import Path

from backend.ai.v2.cohort import Candidate, STRATA, select_review_cohort
from backend.ai.v2.schemas import AnalysisPayload
from backend.database import Database


SQL_DIR = Path(__file__).parents[1] / "backend/database/sql/ai_analysis_v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.limit % len(STRATA):
        parser.error(f"--limit must be divisible by {len(STRATA)}")

    db = Database()
    rows = db.execute_query(
        (SQL_DIR / "select_review_candidates.sql").read_text(encoding="utf-8")
    )
    candidates = [
        Candidate(
            event_id=int(row["event_id"]),
            buyer_nick=row["buyer_nick"],
            stratum=row["stratum"],
            risk_score=float(row["risk_score"]),
        )
        for row in rows
    ]
    cohort = select_review_cohort(candidates, per_stratum=args.limit // len(STRATA))
    counts = Counter(case.stratum for case in cohort)
    print(f"mode={'write' if args.write else 'dry-run'} buyers={len(cohort)} strata={dict(counts)}")
    for case in cohort:
        print(f"{case.stratum}\t{case.buyer_nick}\tevent={case.event_id}\trisk={case.risk_score:.1f}")

    if args.write:
        sql = (SQL_DIR / "upsert_review.sql").read_text(encoding="utf-8")
        payload_sql = (SQL_DIR / "get_review_model_payload.sql").read_text(
            encoding="utf-8"
        )
        for case in cohort:
            payload_rows = db.execute_query(payload_sql, (case.event_id,))
            if not payload_rows:
                raise RuntimeError(f"event {case.event_id} disappeared before write")
            raw_payload = payload_rows[0]["model_payload"]
            if isinstance(raw_payload, str):
                raw_payload = json.loads(raw_payload)
            model_json = AnalysisPayload.model_validate(raw_payload).model_dump_json()
            db.execute_update(sql, (case.event_id, case.stratum, model_json))
        print(f"wrote {len(cohort)} pending review rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
