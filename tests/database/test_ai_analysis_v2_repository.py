import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.ai.v2.repository import AIAnalysisV2Repository, BuyerAnalysis
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
        self.last_name = name
        self.db.statement_names.append(name)
        self.db.statement_params.append((name, params))
        if self.db.fail_on == name:
            raise RuntimeError("write failed")
        return 1

    def fetchone(self):
        return self.db.fetchone_by_name.get(self.last_name)


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
    def __init__(self, rows=None, fail_on=None, fetchone_by_name=None):
        self.rows = rows or []
        self.fail_on = fail_on
        self.statement_names = []
        self.statement_params = []
        self.begin_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.last_params = None
        self.last_sql = None
        self.fetchone_by_name = fetchone_by_name or {}

    @contextmanager
    def get_connection(self):
        yield RecordingConnection(self)

    def execute_query(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        self.statement_names.append(sql.splitlines()[0].removeprefix("-- name: ").strip())
        return self.rows

    def execute_update(self, sql, params=None):
        name = sql.splitlines()[0].removeprefix("-- name: ").strip()
        self.statement_names.append(name)
        self.statement_params.append((name, params))
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


def test_success_records_the_provider_that_produced_the_valid_payload():
    db = RecordingDatabase()
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    repo.persist_success(
        7,
        "buyer",
        window(),
        payload(),
        state(),
        provider="deepseek",
        model="deepseek-v4-flash",
    )

    complete_params = dict(db.statement_params)["complete_run.sql"]
    assert complete_params[:2] == ("deepseek", "deepseek-v4-flash")


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


def test_issue_trends_uses_bound_filters():
    db = RecordingDatabase(rows=[{"issue_code": "material_expectation"}])
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    rows = repo.get_issue_trends(
        date_from="2026-06-01",
        date_to="2026-07-01",
        issue_category="product",
    )

    assert rows[0]["issue_code"] == "material_expectation"
    assert "i.issue_category = %s" in db.last_sql
    assert db.last_params == (
        "2026-06-01",
        "2026-07-01",
        "2026-05-02",
        "2026-06-01",
        "2026-05-02",
        "2026-07-01",
        "product",
    )


def test_issue_trends_supports_all_api_filters():
    db = RecordingDatabase()
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    repo.get_issue_trends(
        "2026-06-01",
        "2026-07-01",
        issue_code="material_expectation",
        status="open",
        severity="medium",
        buyer_type="VIC",
    )

    assert "i.issue_code = %s" in db.last_sql
    assert "i.status = %s" in db.last_sql
    assert "i.severity = %s" in db.last_sql
    assert "tb.buyer_type = %s" in db.last_sql
    assert db.last_params[-4:] == (
        "material_expectation",
        "open",
        "medium",
        "VIC",
    )


class SourceDatabase(RecordingDatabase):
    def __init__(self, rows_by_name):
        super().__init__()
        self.rows_by_name = rows_by_name

    def execute_query(self, sql, params=None):
        name = sql.splitlines()[0].removeprefix("-- name: ").strip()
        self.statement_names.append(name)
        return self.rows_by_name.get(name, [])


def test_load_incremental_source_returns_checkpoint_context_and_profile():
    checkpoint = "2026-07-20 10:00:00"
    db = SourceDatabase(
        {
            "get_source_state.sql": [
                {
                    "analyzed_through_msg_time": checkpoint,
                    "attention_priority": "low",
                    "current_sentiment_label": "Neutral",
                }
            ],
            "get_incremental_chats.sql": [{"content": "新增消息"}],
            "get_open_events.sql": [{"id": 17, "topic_summary": "退货"}],
            "get_buyer_profile.sql": [{"client_monthly_tag": "V2"}],
        }
    )
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    source = repo.load_source("buyer", "incremental")

    assert source.checkpoint.isoformat(sep=" ") == checkpoint
    assert source.chats == [{"content": "新增消息"}]
    assert source.open_events[0]["id"] == 17
    assert source.profile["client_monthly_tag"] == "V2"
    assert "get_incremental_chats.sql" in db.statement_names


def test_continued_event_replaces_existing_event_for_rollup():
    class ExistingRepository(AIAnalysisV2Repository):
        def get_buyer_analysis(self, buyer_nick):
            return BuyerAnalysis(
                customer_state=None,
                events=[
                    {
                        "id": 17,
                        "event_ended_at": "2026-07-19T10:00:00",
                        "sentiment_label": "Neutral",
                        "service_friction": "none",
                        "suggested_action": "旧动作",
                    }
                ],
                issues=[],
            )

    updated = payload().model_copy(deep=True)
    updated.events[0].event_action = "continue_event"
    updated.events[0].related_event_id = 17
    repo = ExistingRepository(db=RecordingDatabase(), sql_dir=SQL_DIR)

    events = repo.events_for_rollup("buyer", updated)

    assert len(events) == 1
    assert events[0].event_id == 17
    assert events[0].suggested_action == "协助退货"


def test_batch_candidates_return_only_buyer_names():
    db = RecordingDatabase(rows=[{"buyer_nick": "a"}, {"buyer_nick": "b"}])
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    assert repo.get_batch_candidates(50) == ["a", "b"]
    assert db.last_params == (50,)


def test_review_decision_is_written_without_touching_v1_cache():
    db = RecordingDatabase(rows=[{"model_payload": payload().model_dump_json()}])
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    result = repo.review_event(9, "approve", None, "")

    assert result == {"event_id": 9, "review_status": "approved"}
    assert db.statement_names == ["get_review_model_payload.sql", "review_event.sql"]


def test_review_snapshot_contains_only_the_selected_event():
    selected = payload().model_dump(mode="json")
    db = RecordingDatabase(rows=[{"model_payload": json.dumps(selected)}])
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    repo.review_event(9, "approve", None, "")

    assert db.last_params == (9,)
    review_params = dict(db.statement_params)["review_event.sql"]
    assert json.loads(review_params[2]) == selected


def test_review_correction_updates_gold_event_and_state_in_one_transaction():
    corrected = payload().model_dump(mode="json")
    db = RecordingDatabase(
        rows=[{"model_payload": json.dumps(corrected)}],
        fetchone_by_name={
            "get_review_event.sql": {"id": 9, "buyer_nick": "buyer", "last_run_id": 7},
            "get_buyer_analysis.sql": {
                "customer_state": None,
                "events": json.dumps(
                    [
                        {
                            "id": 9,
                            "event_ended_at": "2026-07-20T10:05:00",
                            "sentiment_label": "Neutral",
                            "service_friction": "none",
                            "suggested_action": "协助退货",
                        }
                    ]
                ),
                "issues": json.dumps(
                    [
                        {
                            "event_id": 9,
                            "issue_category": "after_sales",
                            "issue_code": "return_request",
                            "issue_detail": "客户提出退货",
                            "severity": "low",
                            "status": "open",
                            "evidence_msg_time": "2026-07-20T10:00:00",
                        }
                    ]
                ),
            },
        }
    )
    repo = AIAnalysisV2Repository(db=db, sql_dir=SQL_DIR)

    result = repo.review_event(9, "correct", corrected, "人工修正")

    assert result == {"event_id": 9, "review_status": "corrected"}
    assert db.begin_count == 1
    assert db.commit_count == 1
    assert db.rollback_count == 0
    assert db.statement_names[-2:] == ["upsert_customer_state.sql", "review_event.sql"]
