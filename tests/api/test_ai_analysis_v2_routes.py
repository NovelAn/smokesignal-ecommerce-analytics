from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.ai.analysis_errors import AIAnalysisUnavailableError
from backend.api import ai_analysis_v2_routes as routes
from backend.main import app


client = TestClient(app)


class FakeRepository:
    def get_buyer_analysis(self, buyer_nick):
        return SimpleNamespace(
            customer_state={"attention_priority": "high"},
            events=[{"id": 9, "topic_summary": "退货"}],
            issues=[
                {"id": 1, "event_id": 9, "issue_code": "return_request"},
                {"id": 2, "event_id": 9, "issue_code": "explanation_unclear"},
            ],
        )


class FakeAnalyzer:
    def analyze_buyer(self, buyer_nick, mode):
        return SimpleNamespace(status="completed", provider="minimax", reason=None)


class FailingAnalyzer:
    def analyze_buyer(self, buyer_nick, mode):
        raise AIAnalysisUnavailableError("provider unavailable")


def test_single_buyer_analysis_returns_events_issues_and_state(monkeypatch):
    monkeypatch.setattr(routes, "get_v2_analyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr(routes, "get_v2_repository", lambda: FakeRepository())

    response = client.post(
        "/api/v2/ai-analysis-v2/buyers/buyer/analyze?mode=full"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert len(body["events"][0]["issues"]) == 2
    assert body["customer_state"]["attention_priority"] == "high"


def test_failed_analysis_returns_503_and_remains_retryable(monkeypatch):
    monkeypatch.setattr(routes, "get_v2_analyzer", lambda: FailingAnalyzer())

    response = client.post(
        "/api/v2/ai-analysis-v2/buyers/buyer/analyze?mode=incremental"
    )

    assert response.status_code == 503
    assert response.json()["detail"]["retryable"] is True


def test_review_correction_requires_note():
    response = client.put(
        "/api/v2/ai-analysis-v2/reviews/9",
        json={
            "action": "correct",
            "gold_payload": {"events": []},
            "note": "",
        },
    )

    assert response.status_code == 422


def test_batch_status_and_cancel_reuse_one_manager(monkeypatch):
    class FakeBatchManager:
        def start(self, limit):
            return "task-1"

        def get(self, task_id):
            return {"task_id": task_id, "status": "running", "processed_buyers": 1}

        def cancel(self, task_id):
            return True

    manager = FakeBatchManager()
    monkeypatch.setattr(routes, "get_v2_batch_manager", lambda: manager)

    started = client.post("/api/v2/ai-analysis-v2/batch?limit=50")
    status = client.get("/api/v2/ai-analysis-v2/batch/task-1")
    cancelled = client.post("/api/v2/ai-analysis-v2/batch/task-1/cancel")

    assert started.json()["task_id"] == "task-1"
    assert status.json()["status"] == "running"
    assert cancelled.json()["status"] == "cancelled"
