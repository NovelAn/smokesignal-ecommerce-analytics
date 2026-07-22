import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.ai.v2.repository import AIAnalysisV2Repository
from backend.ai.v2.schemas import AnalysisPayload, CustomerState


SQL_DIR = Path(__file__).parents[2] / "backend/database/sql/ai_analysis_v2"


def payload() -> AnalysisPayload:
    return AnalysisPayload.model_validate(
        {
            "events": [
                {
                    "event_action": "new_event",
                    "related_event_id": None,
                    "topic_summary": "客户要求退货",
                    "event_started_at": "2026-07-20T10:00:00",
                    "event_ended_at": "2026-07-20T10:05:00",
                    "sentiment_label": "Neutral",
                    "sentiment_score": 0.5,
                    "sentiment_basis": "neutral_business",
                    "peak_emotion": "calm",
                    "service_friction": "none",
                    "resolution_status": "unresolved",
                    "customer_accepted": None,
                    "suggested_action": "协助退货",
                    "issues": [
                        {
                            "issue_category": "after_sales",
                            "issue_code": "return_request",
                            "issue_detail": "客户提出退货",
                            "severity": "low",
                            "owner": "customer",
                            "status": "open",
                            "is_primary": True,
                            "evidence_text": "我要退货",
                            "evidence_msg_time": "2026-07-20T10:00:00",
                        }
                    ],
                }
            ]
        }
    )


def state() -> CustomerState:
    return CustomerState.model_validate(
        {
            "buyer_nick": "buyer",
            "current_sentiment_label": "Neutral",
            "primary_issue_code": "return_request",
            "primary_issue_detail": "客户提出退货",
            "active_issue_count": 1,
            "highest_severity": "low",
            "attention_priority": "low",
            "recommended_action": "协助退货",
            "analyzed_through_msg_time": "2026-07-20T10:05:00",
            "last_run_id": 7,
        }
    )


def window():
    return SimpleNamespace(
        fingerprint="abc",
        source_from_msg_time="2026-07-20T10:00:00",
        source_to_msg_time="2026-07-20T10:05:00",
        source_message_count=2,
    )


class RecordingCursor:
    def __init__(self, db):
        self.db = db
        self.lastrowid = 101

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=None):
        name = sql.splitlines()[0].removeprefix("-- name: ").strip()
        self.db.statement_names.append(name)
        if self.db.fail_on == name:
            raise RuntimeError("write failed")
        return 1


class RecordingConnection:
    def __init__(self, db):
        self.db = db

    def begin(self):
        self.db.begin_count += 1

    def cursor(self):
        return RecordingCursor(self.db)

    def commit(self):
        self.db.commit_count += 1

    def rollback(self):
        self.db.rollback_count += 1


class RecordingDatabase:
    def __init__(self, rows=None, fail_on=None):
        self.rows = rows or []
        self.fail_on = fail_on
        self.statement_names = []
        self.begin_count = 0
        self.commit_count = 0
        self.rollback_count = 0

    @contextmanager
    def get_connection(self):
        yield RecordingConnection(self)

    def execute_query(self, sql, params=None):
        self.statement_names.append(sql.splitlines()[0].removeprefix("-- name: ").strip())
        return self.rows

    def execute_update(self, sql, params=None):
        self.statement_names.append(sql.splitlines()[0].removeprefix("-- name: ").strip())
        return 1


def test_failed_run_does_not_write_results_or_checkpoint():
    db = RecordingDatabase()
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    repo.persist_failure(run_id=7, code="invalid_schema", message="bad payload")

    assert db.statement_names == ["fail_run.sql"]


def test_success_is_one_transaction():
    db = RecordingDatabase()
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    repo.persist_success(
        run_id=7,
        buyer_nick="buyer",
        window=window(),
        payload=payload(),
        state=state(),
    )

    assert db.begin_count == 1
    assert db.commit_count == 1
    assert db.rollback_count == 0
    assert db.statement_names[-2:] == ["upsert_customer_state.sql", "complete_run.sql"]


def test_success_rolls_back_every_write_on_error():
    db = RecordingDatabase(fail_on="upsert_customer_state.sql")
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    with pytest.raises(RuntimeError, match="write failed"):
        repo.persist_success(7, "buyer", window(), payload(), state())

    assert db.commit_count == 0
    assert db.rollback_count == 1


def test_completed_fingerprint_short_circuits_duplicate_analysis():
    db = RecordingDatabase(
        rows=[
            {
                "id": 7,
                "provider": "minimax",
                "model": "MiniMax-M3",
                "result_payload": json.dumps(payload().model_dump(mode="json")),
            }
        ]
    )
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    completed = repo.find_completed_run("buyer", "abc", "v2.0")

    assert completed is not None
    assert completed.run_id == 7
    assert completed.payload == payload()
