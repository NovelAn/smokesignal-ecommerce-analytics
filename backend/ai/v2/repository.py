"""SQL-backed persistence for AI Analysis V2."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.database import Database

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


class AIAnalysisV2Repository:
    def __init__(self, db: Database | None = None, sql_dir: Path | None = None):
        self.db = db or Database(db_name=settings.db_name_to_use or "aliyunDB")
        self.sql_dir = sql_dir or (
            Path(__file__).parents[2] / "database/sql/ai_analysis_v2"
        )

    def _sql(self, name: str) -> str:
        return (self.sql_dir / name).read_text(encoding="utf-8")

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
                        (
                            buyer_nick,
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
                        ),
                    )
                    cursor.execute(
                        self._sql("complete_run.sql"),
                        (payload.model_dump_json(), run_id),
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
        return BuyerAnalysis(
            customer_state=self._decode_json(row.get("customer_state")),
            events=self._decode_json(row.get("events")) or [],
            issues=self._decode_json(row.get("issues")) or [],
        )

    def get_issue_trends(
        self,
        date_from: date | datetime | str,
        date_to: date | datetime | str,
        issue_category: str | None = None,
    ) -> list[dict[str, Any]]:
        start = self._as_date(date_from)
        end = self._as_date(date_to)
        if end <= start:
            raise ValueError("date_to must be after date_from")
        previous_start = start - (end - start)
        sql = self._sql("get_issue_trends.sql").replace(
            "[[OPTIONAL_CONDITION]]",
            "AND i.issue_category = %s" if issue_category else "",
        )
        params: tuple[Any, ...] = (
            start.isoformat(),
            end.isoformat(),
            previous_start.isoformat(),
            start.isoformat(),
            previous_start.isoformat(),
            end.isoformat(),
        )
        if issue_category:
            params += (issue_category,)
        return self.db.execute_query(sql, params)

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
