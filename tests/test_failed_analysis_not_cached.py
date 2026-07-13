"""Regression tests for failed AI analyses being persisted as successful cache."""

import asyncio
import threading
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.api import target_routes
from backend.ai.analyzer_orchestrator import AICacheManager, AnalyzerOrchestrator
from backend.ai.batch_analyzer import BatchAnalyzer, BatchTask, BatchTaskStatus
from backend.ai.deepseek_client import DeepSeekClient
from backend.ai.minimax_client import MiniMaxClient


class _FailingPersonaClient:
    def analyze_buyer_persona(self, *args, **kwargs):
        raise TimeoutError("provider timeout")

    def analyze_buyer_persona_chat(self, *args, **kwargs):
        raise TimeoutError("provider timeout")


class _FailingSentimentClient:
    def analyze_sentiment_intent(self, *args, **kwargs):
        raise TimeoutError("provider timeout")


class _NoRuleFallback:
    def analyze(self, *args, **kwargs):
        raise AssertionError("configured model failures must remain retryable")


class _RecordingCache:
    def __init__(self):
        self.saved = []

    def set_persona(self, *args, **kwargs):
        self.saved.append((args, kwargs))


class _RecordingDB:
    def __init__(self):
        self.updates = []

    def execute_update(self, query, params=None):
        self.updates.append((query, params))
        return 1


class _FakeChatCompletions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        content = (
            '{"sentiment_score":0.5,"sentiment_label":"Neutral",'
            '"intent_distribution":{"Pre-sale Inquiry":1},'
            '"dominant_intent":"Pre-sale Inquiry","complaint_count":0}'
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(
                total_tokens=100,
                prompt_tokens=80,
                completion_tokens=20,
            ),
        )


def test_minimax_sentiment_parse_failure_is_not_a_neutral_result():
    client = MiniMaxClient.__new__(MiniMaxClient)

    with pytest.raises(ValueError, match="JSON"):
        client._parse_sentiment_intent_response("provider returned non-json")


def test_deepseek_sentiment_parse_failure_is_not_a_neutral_result():
    client = DeepSeekClient.__new__(DeepSeekClient)

    with pytest.raises(ValueError, match="JSON"):
        client._parse_sentiment_response("provider returned non-json")


@pytest.mark.parametrize(
    ("client_class", "parser_name"),
    [
        (MiniMaxClient, "_parse_sentiment_intent_response"),
        (DeepSeekClient, "_parse_sentiment_response"),
    ],
)
def test_incomplete_sentiment_json_is_not_filled_with_success_defaults(
    client_class, parser_name
):
    client = client_class.__new__(client_class)

    with pytest.raises(ValueError, match="schema"):
        getattr(client, parser_name)('{"sentiment_label": "Neutral"}')


@pytest.mark.parametrize(
    ("client_class", "parser_name"),
    [
        (MiniMaxClient, "_parse_sentiment_intent_response"),
        (DeepSeekClient, "_parse_sentiment_response"),
    ],
)
def test_sentiment_parser_accepts_first_complete_json_before_extra_text(
    client_class, parser_name
):
    client = client_class.__new__(client_class)
    valid = (
        '{"sentiment_score":0.5,"sentiment_label":"Neutral",'
        '"intent_distribution":{"Pre-sale Inquiry":1},'
        '"dominant_intent":"Pre-sale Inquiry","complaint_count":0}'
    )

    result = getattr(client, parser_name)(valid + '\n额外说明 {"note": "ignore"}')

    assert result["sentiment_label"] == "Neutral"
    assert result["dominant_intent"] == "Pre-sale Inquiry"


def test_minimax_sentiment_call_has_enough_output_budget():
    completions = _FakeChatCompletions()
    client = MiniMaxClient.__new__(MiniMaxClient)
    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    client.model = "MiniMax-M3"

    client.analyze_sentiment_intent("buyer", ["hello"])

    assert completions.last_kwargs["max_tokens"] >= 2000


def test_deepseek_sentiment_call_has_enough_output_budget(monkeypatch):
    completions = _FakeChatCompletions()
    client = DeepSeekClient.__new__(DeepSeekClient)
    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    client.model_chat = "deepseek-v4-flash"
    monkeypatch.setattr(
        "backend.monitoring.cost_monitor.get_cost_monitor",
        lambda: SimpleNamespace(log_api_call=lambda **kwargs: None),
    )

    client.analyze_sentiment_intent("buyer", ["hello"])

    assert completions.last_kwargs["max_tokens"] >= 2000


@pytest.mark.parametrize(
    ("client_class", "openai_path", "api_key_path"),
    [
        (
            MiniMaxClient,
            "backend.ai.minimax_client.OpenAI",
            "backend.ai.minimax_client.settings.minimax_api_key",
        ),
        (
            DeepSeekClient,
            "backend.ai.deepseek_client.OpenAI",
            "backend.ai.deepseek_client.settings.deepseek_api_key",
        ),
    ],
)
def test_ai_clients_have_bounded_read_timeout(
    monkeypatch, client_class, openai_path, api_key_path
):
    captured = {}

    def fake_http_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("httpx.Client", fake_http_client)
    monkeypatch.setattr(openai_path, lambda **kwargs: object())
    monkeypatch.setattr(api_key_path, "test-key")

    client_class()

    assert captured["timeout"].read <= 120


def test_persona_provider_failures_raise_without_writing_cache(monkeypatch):
    orchestrator = AnalyzerOrchestrator.__new__(AnalyzerOrchestrator)
    orchestrator.minimax = _FailingPersonaClient()
    orchestrator.deepseek = _FailingPersonaClient()
    orchestrator.rule_based = _NoRuleFallback()
    orchestrator.cache_manager = _RecordingCache()

    monkeypatch.setattr(
        "backend.ai.analyzer_orchestrator.should_use_deepseek_pro",
        lambda *args, **kwargs: False,
    )

    with pytest.raises(RuntimeError, match="retry"):
        orchestrator.analyze_buyer_persona(
            buyer_nick="buyer",
            profile={},
            chats=[{"content": "hello"}],
            orders=[],
            force_refresh=True,
        )

    assert orchestrator.cache_manager.saved == []


def test_sentiment_provider_failures_do_not_fall_back_to_cacheable_rules():
    analyzer = BatchAnalyzer.__new__(BatchAnalyzer)
    analyzer.minimax_client = _FailingSentimentClient()
    analyzer.deepseek_client = _FailingSentimentClient()
    analyzer.rule_based = _NoRuleFallback()
    analyzer.rate_limiter = SimpleNamespace(wait=lambda: None)

    with pytest.raises(RuntimeError, match="retry"):
        analyzer.analyze_single_buyer(
            "buyer",
            [{"sender_nick": "buyer", "content": "hello"}],
        )


def test_persona_cache_rejects_pending_retry_placeholder():
    cache = AICacheManager.__new__(AICacheManager)
    cache.db = _RecordingDB()

    saved = cache.set_persona(
        "buyer",
        {
            "summary": "AI analysis failed and should be retried",
            "analysis_method": "pending_retry",
        },
        {},
    )

    assert saved is False
    assert cache.db.updates == []


def test_sentiment_cache_rejects_explicit_failure(monkeypatch):
    db = _RecordingDB()
    monkeypatch.setattr("backend.database.Database", lambda *args, **kwargs: db)

    analyzer = BatchAnalyzer.__new__(BatchAnalyzer)
    saved = analyzer.save_analysis_result(
        {
            "buyer_nick": "buyer",
            "sentiment_method": "pending_retry",
            "sentiment_score": 0.5,
            "sentiment_label": "Neutral",
        }
    )

    assert saved is False
    assert db.updates == []


def test_force_refresh_failure_does_not_clear_previous_success(monkeypatch):
    class FailingBatchAnalyzer:
        def __init__(self):
            self.cleared = []

        def force_refresh(self, buyer_nick):
            self.cleared.append(buyer_nick)

        def analyze_single_buyer(self, *args, **kwargs):
            raise RuntimeError("provider failed")

    class FakeOrchestrator:
        def __init__(self):
            self.cleared = []

        def force_refresh(self, buyer_nick):
            self.cleared.append(buyer_nick)

    class FakeDB:
        def execute_query(self, query, params=None):
            if "target_buyers_precomputed" in query:
                return [{"buyer_nick": "buyer", "last_chat_date": "2026-07-13 10:00:00"}]
            return [{"sender_nick": "buyer", "content": "hello"}]

    batch = FailingBatchAnalyzer()
    orchestrator = FakeOrchestrator()
    monkeypatch.setattr(
        "backend.ai.batch_analyzer.get_batch_analyzer", lambda: batch
    )
    monkeypatch.setattr(
        "backend.ai.analyzer_orchestrator.get_analyzer_orchestrator",
        lambda: orchestrator,
    )
    monkeypatch.setattr("backend.database.Database", lambda *args, **kwargs: FakeDB())
    monkeypatch.setattr(
        "backend.database.BuyerQueries.get_chat_messages",
        lambda *args, **kwargs: ("SELECT chats", []),
    )

    with pytest.raises(HTTPException):
        asyncio.run(
            target_routes.force_refresh_analysis(
                "buyer",
                refresh_type="sentiment",
                reanalyze=True,
                analysis_mode="full",
            )
        )

    assert batch.cleared == []
    assert orchestrator.cleared == []


def test_batch_save_failure_is_counted_as_failure(monkeypatch):
    analyzer = BatchAnalyzer.__new__(BatchAnalyzer)
    analyzer.tasks = {"task": BatchTask(task_id="task")}
    analyzer.task_lock = threading.Lock()
    analyzer.max_workers = 1
    analyzer.get_buyers_needing_analysis = lambda limit: [
        {"buyer_nick": "buyer", "sentiment_analyzed_last_chat_date": None}
    ]
    analyzer.fetch_chats_for_analysis = lambda *args, **kwargs: (
        [
            {
                "sender_nick": "buyer",
                "content": "hello",
                "msg_time": "2026-07-13 10:00:00",
            }
        ],
        False,
        None,
    )
    analyzer.analyze_single_buyer = lambda *args, **kwargs: {
        "buyer_nick": "buyer",
        "sentiment_score": 0.8,
        "sentiment_label": "Positive",
        "sentiment_method": "minimax_m3",
    }
    analyzer.save_analysis_result = lambda *args, **kwargs: False

    monkeypatch.setattr(
        "backend.ai.analyzer_orchestrator.get_analyzer_orchestrator",
        lambda: object(),
    )

    analyzer._run_batch_analysis("task", 1)

    task = analyzer.tasks["task"]
    assert task.processed_buyers == 0
    assert task.failed_buyers == 1
    assert task.status is BatchTaskStatus.FAILED
