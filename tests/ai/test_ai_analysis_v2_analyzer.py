import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from backend.ai.analysis_errors import AIAnalysisUnavailableError
from backend.ai.v2.analyzer import AIAnalysisV2Analyzer
from backend.ai.v2.rollup import PersistedEvent, PersistedIssue


def valid_payload_json() -> str:
    return json.dumps(
        {
            "events": [
                {
                    "event_action": "new_event",
                    "related_event_id": None,
                    "topic_summary": "客户正常咨询退货",
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
        },
        ensure_ascii=False,
    )


class SequenceClient:
    model = "test-model"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def analyze_v2(self, prompt):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class AlwaysFail:
    model = "failed-model"

    def __init__(self):
        self.calls = 0

    def analyze_v2(self, prompt):
        self.calls += 1
        raise RuntimeError("provider failed")


class RecordingRepository:
    def __init__(self, profile=None):
        self.profile = profile or {"client_monthly_tag": "V0"}
        self.successes = []
        self.failures = []
        self.checkpoint_updates = []
        self.latest_state = None

    def load_source(self, buyer_nick, mode):
        return SimpleNamespace(
            chats=[
                {
                    "user_nick": buyer_nick,
                    "sender_nick": buyer_nick,
                    "msg_time": datetime(2026, 7, 20, 10),
                    "content": "我要退货",
                }
            ],
            checkpoint=None,
            open_events=[],
            profile=self.profile,
            customer_state=None,
        )

    def find_completed_run(self, *args):
        return None

    def start_run(self, *args, **kwargs):
        return 7

    def events_for_rollup(self, buyer_nick, payload):
        event = payload.events[0]
        issue = event.issues[0]
        return [
            PersistedEvent(
                buyer_nick=buyer_nick,
                event_ended_at=event.event_ended_at,
                sentiment_label=event.sentiment_label,
                service_friction=event.service_friction,
                suggested_action=event.suggested_action,
                issues=(
                    PersistedIssue(
                        issue_category=issue.issue_category,
                        issue_code=issue.issue_code,
                        issue_detail=issue.issue_detail,
                        severity=issue.severity,
                        status=issue.status,
                        last_seen_at=event.event_ended_at,
                    ),
                ),
            )
        ]

    def persist_success(self, **kwargs):
        self.successes.append(kwargs)
        self.latest_state = kwargs["state"]
        self.checkpoint_updates.append(kwargs["state"].analyzed_through_msg_time)

    def persist_failure(self, run_id, code, message):
        self.failures.append((run_id, code, message))

    def get_buyer_analysis(self, buyer_nick):
        return SimpleNamespace(customer_state=self.latest_state)


def make_analyzer(repo, minimax, deepseek):
    return AIAnalysisV2Analyzer(
        repository=repo,
        minimax=minimax,
        deepseek=deepseek,
        clock=lambda: datetime(2026, 7, 22, 12),
    )


def test_invalid_minimax_schema_retries_once_before_deepseek():
    repo = RecordingRepository()
    minimax = SequenceClient(["not json", valid_payload_json()])
    deepseek = SequenceClient([valid_payload_json()])

    result = make_analyzer(repo, minimax, deepseek).analyze_buyer("buyer", "full")

    assert minimax.calls == 2
    assert deepseek.calls == 0
    assert result.provider == "minimax"
    assert len(repo.successes) == 1


def test_all_provider_failures_only_record_failure():
    repo = RecordingRepository(profile={"client_monthly_tag": "V3"})

    with pytest.raises(AIAnalysisUnavailableError):
        make_analyzer(repo, AlwaysFail(), AlwaysFail()).analyze_buyer("buyer", "full")

    assert repo.successes == []
    assert len(repo.failures) == 1
    assert repo.checkpoint_updates == []


def test_low_value_customer_does_not_use_deepseek_after_minimax_failure():
    repo = RecordingRepository(profile={"client_monthly_tag": "V0"})
    deepseek = SequenceClient([valid_payload_json()])

    with pytest.raises(AIAnalysisUnavailableError):
        make_analyzer(repo, AlwaysFail(), deepseek).analyze_buyer("buyer", "full")

    assert deepseek.calls == 0
