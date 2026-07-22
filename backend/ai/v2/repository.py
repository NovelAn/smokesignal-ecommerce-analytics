"""SQL-backed persistence for AI Analysis V2."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.database import Database

from .rollup import PersistedEvent, PersistedIssue, build_customer_state
from .schemas import AnalysisPayload, CustomerState


@dataclass(frozen=True)
class CompletedRun:
    run_id: int
    provider: str | None
    model: str | None
    payload: AnalysisPayload


@dataclass(frozen=True)
class BuyerAnalysis:
    customer_state: dict[str, Any] | None
    events: list[dict[str, Any]]
    issues: list[dict[str, Any]]


@dataclass(frozen=True)
class AnalysisSource:
    chats: list[dict[str, Any]]
    checkpoint: datetime | None
    open_events: list[dict[str, Any]]
    profile: dict[str, Any]
    customer_state: dict[str, Any] | None


class AIAnalysisV2Repository:
    def __init__(self, db: Database | None = None, sql_dir: Path | None = None):
        self.db = db or Database(db_name=settings.db_name_to_use or "aliyunDB")
        self.sql_dir = sql_dir or (
            Path(__file__).parents[2] / "database/sql/ai_analysis_v2"
        )

    def _sql(self, name: str) -> str:
        return (self.sql_dir / name).read_text(encoding="utf-8")

    def load_source(self, buyer_nick: str, mode: str) -> AnalysisSource:
        if mode not in {"full", "incremental"}:
            raise ValueError("mode must be full or incremental")
        state_rows = self.db.execute_query(
            self._sql("get_source_state.sql"), (buyer_nick,)
        )
        customer_state = state_rows[0] if state_rows else None
        checkpoint = self._as_datetime(
            customer_state.get("analyzed_through_msg_time")
            if customer_state
            else None
        )
        if mode == "incremental" and checkpoint is not None:
            chats = self.db.execute_query(
                self._sql("get_incremental_chats.sql"),
                (buyer_nick, checkpoint, buyer_nick, checkpoint),
            )
        else:
            chats = self.db.execute_query(
                self._sql("get_full_chats.sql"), (buyer_nick,)
            )
            checkpoint = None
        open_events = self.db.execute_query(
            self._sql("get_open_events.sql"), (buyer_nick,)
        )
        profile_rows = self.db.execute_query(
            self._sql("get_buyer_profile.sql"), (buyer_nick,)
        )
        return AnalysisSource(
            chats=chats,
            checkpoint=checkpoint,
            open_events=open_events,
            profile=profile_rows[0] if profile_rows else {},
            customer_state=customer_state,
        )

    def start_run(
        self,
        buyer_nick: str,
        mode: str,
        window: Any,
        prompt_version: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> int:
        return self.db.execute_update(
            self._sql("start_run.sql"),
            (
                buyer_nick,
                mode,
                provider,
                model,
                prompt_version,
                window.fingerprint,
                window.source_from_msg_time,
                window.source_to_msg_time,
                window.source_message_count,
            ),
        )

    def find_completed_run(
        self, buyer_nick: str, fingerprint: str, prompt_version: str
    ) -> CompletedRun | None:
        rows = self.db.execute_query(
            self._sql("get_completed_run.sql"),
            (buyer_nick, fingerprint, prompt_version),
        )
        if not rows:
            return None
        row = rows[0]
        raw_payload = row["result_payload"]
        if isinstance(raw_payload, str):
            raw_payload = json.loads(raw_payload)
        return CompletedRun(
            run_id=row["id"],
            provider=row.get("provider"),
            model=row.get("model"),
            payload=AnalysisPayload.model_validate(raw_payload),
        )

    def persist_failure(self, run_id: int, code: str, message: str) -> None:
        self.db.execute_update(
            self._sql("fail_run.sql"),
            (code[:64], message[:500], run_id),
        )

    def persist_success(
        self,
        run_id: int,
        buyer_nick: str,
        window: Any,
        payload: AnalysisPayload,
        state: CustomerState,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        del window  # fingerprint and source range are already fixed by start_run
        with self.db.get_connection() as connection:
            try:
                connection.begin()
                with connection.cursor() as cursor:
                    self._write_events(cursor, run_id, buyer_nick, payload)
                    last_event_at = max(
                        event.event_ended_at for event in payload.events
                    )
                    cursor.execute(
                        self._sql("upsert_customer_state.sql"),
                        self._state_params(state, run_id, last_event_at),
                    )
                    cursor.execute(
                        self._sql("complete_run.sql"),
                        (provider, model, payload.model_dump_json(), run_id),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _write_events(
        self, cursor: Any, run_id: int, buyer_nick: str, payload: AnalysisPayload
    ) -> None:
        for event_index, event in enumerate(payload.events):
            if event.event_action == "continue_event":
                event_id = event.related_event_id
                cursor.execute(
                    self._sql("update_event.sql"),
                    (
                        run_id,
                        event.topic_summary,
                        event.event_started_at,
                        event.event_ended_at,
                        event.sentiment_label,
                        event.sentiment_score,
                        event.sentiment_basis,
                        event.peak_emotion,
                        event.service_friction,
                        event.resolution_status,
                        event.customer_accepted,
                        event.suggested_action,
                        event_id,
                        buyer_nick,
                    ),
                )
            else:
                cursor.execute(
                    self._sql("insert_event.sql"),
                    (
                        buyer_nick,
                        run_id,
                        run_id,
                        event_index,
                        event.topic_summary,
                        event.event_started_at,
                        event.event_ended_at,
                        event.sentiment_label,
                        event.sentiment_score,
                        event.sentiment_basis,
                        event.peak_emotion,
                        event.service_friction,
                        event.resolution_status,
                        event.customer_accepted,
                        event.suggested_action,
                    ),
                )
                event_id = cursor.lastrowid

            for issue in event.issues:
                cursor.execute(
                    self._sql("insert_issue.sql"),
                    (
                        event_id,
                        buyer_nick,
                        issue.issue_category,
                        issue.issue_code,
                        issue.issue_detail,
                        issue.severity,
                        issue.owner,
                        issue.status,
                        issue.is_primary,
                        issue.evidence_text,
                        issue.evidence_msg_time,
                    ),
                )

    def get_buyer_analysis(self, buyer_nick: str) -> BuyerAnalysis:
        rows = self.db.execute_query(
            self._sql("get_buyer_analysis.sql"),
            (buyer_nick, buyer_nick, buyer_nick),
        )
        if not rows:
            return BuyerAnalysis(None, [], [])
        row = rows[0]
        return self._buyer_analysis_from_row(row)

    def get_issue_trends(
        self,
        date_from: date | datetime | str,
        date_to: date | datetime | str,
        issue_category: str | None = None,
        issue_code: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        buyer_type: str | None = None,
    ) -> list[dict[str, Any]]:
        start = self._as_date(date_from)
        end = self._as_date(date_to)
        if end <= start:
            raise ValueError("date_to must be after date_from")
        previous_start = start - (end - start)
        filters = [
            ("i.issue_category", issue_category),
            ("i.issue_code", issue_code),
            ("i.status", status),
            ("i.severity", severity),
            ("tb.buyer_type", buyer_type),
        ]
        conditions = [f"AND {column} = %s" for column, value in filters if value]
        sql = self._sql("get_issue_trends.sql").replace(
            "[[OPTIONAL_CONDITION]]", "\n    ".join(conditions)
        )
        params: tuple[Any, ...] = (
            start.isoformat(),
            end.isoformat(),
            previous_start.isoformat(),
            start.isoformat(),
            previous_start.isoformat(),
            end.isoformat(),
        )
        params += tuple(value for _, value in filters if value)
        return self.db.execute_query(sql, params)

    def get_batch_candidates(self, limit: int = 50) -> list[str]:
        rows = self.db.execute_query(
            self._sql("get_batch_candidates.sql"), (limit,)
        )
        return [row["buyer_nick"] for row in rows]

    def get_affected_buyers(
        self,
        issue_code: str,
        date_from: date | datetime | str,
        date_to: date | datetime | str,
    ) -> list[dict[str, Any]]:
        return self.db.execute_query(
            self._sql("get_affected_buyers.sql"),
            (issue_code, date_from, date_to),
        )

    def list_reviews(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        rows = self.db.execute_query(
            self._sql("list_reviews.sql"), (limit, offset)
        )
        for row in rows:
            row["model_payload"] = self._decode_json(row.get("model_payload"))
            row["gold_payload"] = self._decode_json(row.get("gold_payload"))
            row["dialogue"] = self._decode_json(row.get("dialogue")) or []
        return {"items": rows, "count": len(rows), "limit": limit, "offset": offset}

    def review_event(
        self,
        event_id: int,
        action: str,
        gold_payload: dict[str, Any] | None,
        note: str,
        reviewed_by: str = "api",
    ) -> dict[str, Any]:
        statuses = {
            "approve": "approved",
            "correct": "corrected",
            "reject": "rejected",
        }
        if action not in statuses:
            raise ValueError("invalid review action")
        if action in {"correct", "reject"} and not note.strip():
            raise ValueError("correction and rejection require a note")
        if action == "correct":
            validated = AnalysisPayload.model_validate(gold_payload)
            if len(validated.events) != 1:
                raise ValueError("event correction requires exactly one event")
            return self._persist_correction(
                event_id, validated, note, reviewed_by
            )
        else:
            gold_json = None
        status = statuses[action]
        self.db.execute_update(
            self._sql("review_event.sql"),
            (status, gold_json, note or None, reviewed_by, event_id),
        )
        return {"event_id": event_id, "review_status": status}

    def _persist_correction(
        self,
        event_id: int,
        payload: AnalysisPayload,
        note: str,
        reviewed_by: str,
    ) -> dict[str, Any]:
        with self.db.get_connection() as connection:
            try:
                connection.begin()
                with connection.cursor() as cursor:
                    cursor.execute(self._sql("get_review_event.sql"), (event_id,))
                    target = cursor.fetchone()
                    if not target:
                        raise ValueError("review event not found")
                    event = payload.events[0]
                    cursor.execute(
                        self._sql("update_event.sql"),
                        (
                            target["last_run_id"],
                            event.topic_summary,
                            event.event_started_at,
                            event.event_ended_at,
                            event.sentiment_label,
                            event.sentiment_score,
                            event.sentiment_basis,
                            event.peak_emotion,
                            event.service_friction,
                            event.resolution_status,
                            event.customer_accepted,
                            event.suggested_action,
                            event_id,
                            target["buyer_nick"],
                        ),
                    )
                    cursor.execute(
                        self._sql("delete_event_issues.sql"), (event_id,)
                    )
                    for issue in event.issues:
                        cursor.execute(
                            self._sql("insert_issue.sql"),
                            (
                                event_id,
                                target["buyer_nick"],
                                issue.issue_category,
                                issue.issue_code,
                                issue.issue_detail,
                                issue.severity,
                                issue.owner,
                                issue.status,
                                issue.is_primary,
                                issue.evidence_text,
                                issue.evidence_msg_time,
                            ),
                        )
                    cursor.execute(
                        self._sql("get_buyer_analysis.sql"),
                        (
                            target["buyer_nick"],
                            target["buyer_nick"],
                            target["buyer_nick"],
                        ),
                    )
                    row = cursor.fetchone()
                    analysis = self._buyer_analysis_from_row(row)
                    events = self._persisted_events(
                        target["buyer_nick"], analysis
                    )
                    state = build_customer_state(
                        events,
                        datetime.now(),
                        buyer_nick=target["buyer_nick"],
                        last_run_id=target["last_run_id"],
                    )
                    cursor.execute(
                        self._sql("upsert_customer_state.sql"),
                        self._state_params(
                            state,
                            target["last_run_id"],
                            max(item.event_ended_at for item in events),
                        ),
                    )
                    cursor.execute(
                        self._sql("review_event.sql"),
                        (
                            "corrected",
                            payload.model_dump_json(),
                            note,
                            reviewed_by,
                            event_id,
                        ),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {"event_id": event_id, "review_status": "corrected"}

    def events_for_rollup(
        self, buyer_nick: str, payload: AnalysisPayload
    ) -> list[PersistedEvent]:
        analysis = self.get_buyer_analysis(buyer_nick)
        events = self._persisted_events(buyer_nick, analysis)
        for event in payload.events:
            if event.related_event_id is not None:
                events = [
                    existing
                    for existing in events
                    if existing.event_id != event.related_event_id
                ]
            events.append(
                PersistedEvent(
                    event_id=event.related_event_id,
                    buyer_nick=buyer_nick,
                    event_ended_at=event.event_ended_at,
                    sentiment_label=event.sentiment_label,
                    service_friction=event.service_friction,
                    suggested_action=event.suggested_action,
                    issues=tuple(
                        PersistedIssue(
                            issue_category=issue.issue_category,
                            issue_code=issue.issue_code,
                            issue_detail=issue.issue_detail,
                            severity=issue.severity,
                            status=issue.status,
                            last_seen_at=issue.evidence_msg_time
                            or event.event_ended_at,
                        )
                        for issue in event.issues
                    ),
                )
            )
        return events

    def _persisted_events(
        self, buyer_nick: str, analysis: BuyerAnalysis
    ) -> list[PersistedEvent]:
        issues_by_event: dict[int, list[PersistedIssue]] = {}
        for issue in analysis.issues:
            event_id = int(issue["event_id"])
            issues_by_event.setdefault(event_id, []).append(
                PersistedIssue(
                    issue_category=issue["issue_category"],
                    issue_code=issue["issue_code"],
                    issue_detail=issue["issue_detail"],
                    severity=issue["severity"],
                    status=issue["status"],
                    last_seen_at=self._as_datetime(
                        issue.get("evidence_msg_time") or issue.get("created_at")
                    )
                    or self._as_datetime(
                        next(
                            event["event_ended_at"]
                            for event in analysis.events
                            if int(event["id"]) == event_id
                        )
                    ),
                )
            )
        return [
            PersistedEvent(
                event_id=int(event["id"]),
                buyer_nick=buyer_nick,
                event_ended_at=self._as_datetime(event["event_ended_at"]),
                sentiment_label=event["sentiment_label"],
                service_friction=event["service_friction"],
                suggested_action=event["suggested_action"],
                issues=tuple(issues_by_event.get(int(event["id"]), [])),
            )
            for event in analysis.events
        ]

    def _buyer_analysis_from_row(self, row: dict[str, Any] | None) -> BuyerAnalysis:
        if not row:
            return BuyerAnalysis(None, [], [])
        return BuyerAnalysis(
            customer_state=self._decode_json(row.get("customer_state")),
            events=self._decode_json(row.get("events")) or [],
            issues=self._decode_json(row.get("issues")) or [],
        )

    @staticmethod
    def _state_params(
        state: CustomerState, run_id: int, last_event_at: datetime
    ) -> tuple[Any, ...]:
        return (
            state.buyer_nick,
            state.current_sentiment_label,
            state.primary_issue_code,
            state.primary_issue_detail,
            state.active_issue_count,
            state.highest_severity,
            state.attention_priority,
            state.recommended_action,
            state.analyzed_through_msg_time,
            last_event_at,
            run_id,
        )

    @staticmethod
    def _decode_json(value: Any) -> Any:
        return json.loads(value) if isinstance(value, str) else value

    @staticmethod
    def _as_date(value: date | datetime | str) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @staticmethod
    def _as_datetime(value: datetime | str | None) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)
