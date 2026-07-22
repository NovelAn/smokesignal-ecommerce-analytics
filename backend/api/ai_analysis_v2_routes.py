"""AI Analysis V2 API routes."""

import asyncio
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from functools import lru_cache
from enum import IntEnum
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, model_validator

from backend.ai.analysis_errors import AIAnalysisUnavailableError
from backend.ai.v2.analyzer import AIAnalysisV2Analyzer
from backend.ai.v2.repository import AIAnalysisV2Repository, BuyerAnalysis


router = APIRouter(prefix="/api/v2/ai-analysis-v2", tags=["ai_analysis_v2"])


class TrendDays(IntEnum):
    DAYS_30 = 30
    DAYS_90 = 90
    DAYS_180 = 180


class ReviewRequest(BaseModel):
    action: Literal["approve", "correct", "reject"]
    gold_payload: dict[str, Any] | None = None
    note: str = ""

    @model_validator(mode="after")
    def require_review_data(self) -> "ReviewRequest":
        if self.action in {"correct", "reject"} and not self.note.strip():
            raise ValueError("correction and rejection require a note")
        if self.action == "correct" and self.gold_payload is None:
            raise ValueError("correction requires gold_payload")
        return self


@lru_cache(maxsize=1)
def get_v2_repository() -> AIAnalysisV2Repository:
    return AIAnalysisV2Repository()


@lru_cache(maxsize=1)
def get_v2_analyzer() -> AIAnalysisV2Analyzer:
    return AIAnalysisV2Analyzer()


def _analysis_response(
    analysis: BuyerAnalysis,
    *,
    status: str | None = None,
    provider: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    issues_by_event: dict[int, list[dict[str, Any]]] = {}
    for issue in analysis.issues:
        issues_by_event.setdefault(int(issue["event_id"]), []).append(issue)
    events = [
        {**event, "issues": issues_by_event.get(int(event["id"]), [])}
        for event in analysis.events
    ]
    response = {
        "customer_state": analysis.customer_state,
        "events": events,
        "issues": analysis.issues,
    }
    if status is not None:
        response.update(status=status, provider=provider, reason=reason)
    return response


@router.post("/buyers/{buyer_nick}/analyze")
async def analyze_buyer_v2(
    buyer_nick: str,
    mode: Literal["full", "incremental"] = "incremental",
):
    try:
        result = await asyncio.to_thread(
            get_v2_analyzer().analyze_buyer, buyer_nick, mode
        )
    except AIAnalysisUnavailableError as error:
        raise HTTPException(
            503, detail={"message": str(error), "retryable": True}
        ) from error
    analysis = await asyncio.to_thread(
        get_v2_repository().get_buyer_analysis, buyer_nick
    )
    return _analysis_response(
        analysis,
        status=result.status,
        provider=result.provider,
        reason=result.reason,
    )


@router.get("/buyers/{buyer_nick}")
async def get_buyer_v2(buyer_nick: str):
    analysis = await asyncio.to_thread(
        get_v2_repository().get_buyer_analysis, buyer_nick
    )
    return _analysis_response(analysis)


@router.get("/trends")
async def get_issue_trends(
    days: TrendDays = TrendDays.DAYS_30,
    issue_category: str | None = None,
    issue_code: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    buyer_type: str | None = None,
):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=days)
    items = await asyncio.to_thread(
        get_v2_repository().get_issue_trends,
        start,
        end,
        issue_category,
        issue_code,
        status,
        severity,
        buyer_type,
    )
    return {"items": items, "date_from": start, "date_to": end}


@router.get("/reviews")
async def get_reviews(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return await asyncio.to_thread(
        get_v2_repository().list_reviews, limit, offset
    )


@router.get("/trends/{issue_code}/buyers")
async def get_affected_buyers(
    issue_code: str,
    days: TrendDays = TrendDays.DAYS_30,
):
    end = date.today() + timedelta(days=1)
    start = end - timedelta(days=days)
    items = await asyncio.to_thread(
        get_v2_repository().get_affected_buyers,
        issue_code,
        start,
        end,
    )
    return {"items": items, "date_from": start, "date_to": end}


@router.put("/reviews/{event_id}")
async def review_event(event_id: int, request: ReviewRequest):
    return await asyncio.to_thread(
        get_v2_repository().review_event,
        event_id,
        request.action,
        request.gold_payload,
        request.note,
    )


@dataclass
class BatchState:
    task_id: str
    status: str = "pending"
    total_buyers: int = 0
    processed_buyers: int = 0
    successful_buyers: int = 0
    failed_buyers: int = 0
    error: str | None = None


class V2BatchManager:
    def __init__(self):
        self.tasks: dict[str, BatchState] = {}
        self._lock = threading.Lock()

    def start(self, limit: int) -> str:
        task_id = f"ai_v2_{uuid.uuid4().hex[:12]}"
        with self._lock:
            self.tasks[task_id] = BatchState(task_id)
        threading.Thread(
            target=self._run, args=(task_id, limit), daemon=True
        ).start()
        return task_id

    def _run(self, task_id: str, limit: int) -> None:
        try:
            buyers = get_v2_repository().get_batch_candidates(limit)
            with self._lock:
                task = self.tasks[task_id]
                task.status = "running"
                task.total_buyers = len(buyers)
            for buyer_nick in buyers:
                with self._lock:
                    if self.tasks[task_id].status == "cancelled":
                        return
                try:
                    get_v2_analyzer().analyze_buyer(buyer_nick, "incremental")
                    successful = True
                except Exception:
                    successful = False
                with self._lock:
                    task = self.tasks[task_id]
                    task.processed_buyers += 1
                    if successful:
                        task.successful_buyers += 1
                    else:
                        task.failed_buyers += 1
            with self._lock:
                if self.tasks[task_id].status != "cancelled":
                    self.tasks[task_id].status = "completed"
        except Exception as error:
            with self._lock:
                task = self.tasks[task_id]
                task.status = "failed"
                task.error = str(error)

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            task = self.tasks.get(task_id)
            return asdict(task) if task else None

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task or task.status in {"completed", "failed", "cancelled"}:
                return False
            task.status = "cancelled"
            return True


@lru_cache(maxsize=1)
def get_v2_batch_manager() -> V2BatchManager:
    return V2BatchManager()


@router.post("/batch")
async def start_batch(limit: int = Query(50, ge=1, le=500)):
    task_id = get_v2_batch_manager().start(limit)
    return {"task_id": task_id, "status": "pending"}


@router.get("/batch/{task_id}")
async def get_batch(task_id: str):
    task = get_v2_batch_manager().get(task_id)
    if task is None:
        raise HTTPException(404, detail=f"任务 {task_id} 不存在")
    return task


@router.post("/batch/{task_id}/cancel")
async def cancel_batch(task_id: str):
    if not get_v2_batch_manager().cancel(task_id):
        raise HTTPException(404, detail=f"任务 {task_id} 不存在或已结束")
    return {"task_id": task_id, "status": "cancelled"}
