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
from backend.ai.prompts.sentiment_intent_prompt import build_sentiment_intent_prompt


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
            '"sentiment_basis":"neutral_business","sentiment_evidence":"",'
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
        '"sentiment_basis":"neutral_business","sentiment_evidence":"",'
        '"intent_distribution":{"Pre-sale Inquiry":1},'
        '"dominant_intent":"Pre-sale Inquiry","complaint_count":0}'
    )

    result = getattr(client, parser_name)(valid + '\n额外说明 {"note": "ignore"}')

    assert result["sentiment_label"] == "Neutral"
    assert result["dominant_intent"] == "Pre-sale Inquiry"


def test_sentiment_parser_preserves_contextual_basis_and_evidence():
    client = MiniMaxClient.__new__(MiniMaxClient)
    valid = (
        '{"sentiment_score":0.5,"sentiment_label":"Neutral",'
        '"sentiment_basis":"authenticity_concern",'
        '"sentiment_evidence":"我怀疑是假货",'
        '"intent_distribution":{"Post-sale Support":1},'
        '"dominant_intent":"Post-sale Support","complaint_count":0}'
    )

    result = client._parse_sentiment_intent_response(valid)

    assert result["sentiment_basis"] == "authenticity_concern"
    assert result["sentiment_evidence"] == "我怀疑是假货"


def test_sentiment_parser_rejects_result_without_contextual_basis():
    client = MiniMaxClient.__new__(MiniMaxClient)
    missing_basis = (
        '{"sentiment_score":0.2,"sentiment_label":"Negative",'
        '"intent_distribution":{"Complaint":1},'
        '"dominant_intent":"Complaint","complaint_count":1}'
    )

    with pytest.raises(ValueError, match="schema"):
        client._parse_sentiment_intent_response(missing_basis)


def test_minimax_sentiment_call_does_not_truncate_reasoning_before_json():
    completions = _FakeChatCompletions()
    client = MiniMaxClient.__new__(MiniMaxClient)
    client.client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    client.model = "MiniMax-M3"

    client.analyze_sentiment_intent("buyer", ["hello"])

    assert "max_tokens" not in completions.last_kwargs


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


def test_sentiment_schema_failure_retries_minimax_before_deepseek():
    class RetryableMiniMax:
        def __init__(self):
            self.calls = 0

        def analyze_sentiment_intent(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise ValueError("Invalid sentiment/intent response schema")
            return {
                "sentiment_score": 0.5,
                "sentiment_label": "Neutral",
                "sentiment_basis": "neutral_business",
                "sentiment_evidence": "",
                "intent_distribution": {"Post-sale Support": 1},
                "dominant_intent": "Post-sale Support",
                "complaint_count": 0,
            }

    minimax = RetryableMiniMax()
    analyzer = BatchAnalyzer.__new__(BatchAnalyzer)
    analyzer.minimax_client = minimax
    analyzer.deepseek_client = _FailingSentimentClient()
    analyzer.rate_limiter = SimpleNamespace(wait=lambda: None)

    result = analyzer.analyze_single_buyer(
        "buyer",
        [{"sender_nick": "buyer", "content": "正常退货"}],
    )

    assert minimax.calls == 2
    assert result["sentiment_label"] == "Neutral"
    assert result["sentiment_method"] == "minimax_m3"


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


def _post_process_sentiment(
    messages,
    score,
    label="Negative",
    basis="neutral_business",
    evidence="",
    intent_distribution=None,
):
    analyzer = BatchAnalyzer.__new__(BatchAnalyzer)
    return analyzer._post_process_sentiment(
        "buyer",
        messages,
        {
            "sentiment_score": score,
            "sentiment_label": label,
            "sentiment_basis": basis,
            "sentiment_evidence": evidence,
            "intent_distribution": intent_distribution or {
                "Pre-sale Inquiry": 0,
                "Post-sale Support": 0,
                "Logistics": 0,
                "Usage Guide": 0,
                "Complaint": 0,
            },
            "dominant_intent": "Unknown",
            "complaint_count": 0,
        },
        method="minimax_m3",
    )


def test_post_process_derives_label_from_score_boundaries():
    result = _post_process_sentiment(["包装破损，想换货"], 0.42)

    assert result["sentiment_score"] == 0.42
    assert result["sentiment_label"] == "Neutral"


def test_post_process_rejects_negative_for_neutral_business_context():
    result = _post_process_sentiment(
        ["太薄了，请帮我预约退货"],
        0.35,
        basis="neutral_business",
    )

    assert result["sentiment_score"] == 0.5
    assert result["sentiment_label"] == "Neutral"


def test_post_process_keeps_model_negative_for_explicit_complaint_basis():
    result = _post_process_sentiment(
        ["我要投诉"],
        0.2,
        basis="explicit_complaint",
        evidence="我要投诉",
    )

    assert result["sentiment_score"] == 0.2
    assert result["sentiment_label"] == "Negative"


def test_post_process_treats_authenticity_concern_as_neutral():
    result = _post_process_sentiment(
        ["我怀疑是假货"],
        0.2,
        basis="authenticity_concern",
        evidence="我怀疑是假货",
    )

    assert result["sentiment_score"] == 0.5
    assert result["sentiment_label"] == "Neutral"


def test_post_process_does_not_treat_authenticity_concern_as_complaint():
    result = _post_process_sentiment(
        ["我怀疑是假货，可以帮我核实吗"],
        0.45,
        label="Neutral",
        basis="authenticity_concern",
        evidence="我怀疑是假货",
        intent_distribution={
            "Pre-sale Inquiry": 0,
            "Post-sale Support": 1,
            "Logistics": 0,
            "Usage Guide": 0,
            "Complaint": 1,
        },
    )

    assert result["intent_distribution"]["Complaint"] == 0
    assert result["complaint_count"] == 0
    assert result["dominant_intent"] == "Post-sale Support"


def test_post_process_recognizes_strong_accusation_as_negative_evidence():
    result = _post_process_sentiment(
        ["你们就是虚假宣传"],
        0.3,
        basis="strong_negative_evaluation",
        evidence="你们就是虚假宣传",
    )

    assert result["sentiment_score"] == 0.3
    assert result["sentiment_label"] == "Negative"


def test_post_process_recognizes_abuse_as_negative_evidence():
    result = _post_process_sentiment(
        ["你这个狗懒子"],
        0.2,
        basis="abuse_or_threat",
        evidence="你这个狗懒子",
    )

    assert result["sentiment_score"] == 0.2
    assert result["sentiment_label"] == "Negative"


def test_analyze_single_buyer_sends_chronological_full_dialogue_to_model():
    class CapturingClient:
        def __init__(self):
            self.messages = None

        def analyze_sentiment_intent(self, buyer_nick, messages, is_incremental=False):
            self.messages = messages
            return {
                "sentiment_score": 0.5,
                "sentiment_label": "Neutral",
                "sentiment_basis": "neutral_business",
                "sentiment_evidence": "",
                "intent_distribution": {},
                "dominant_intent": "Unknown",
                "complaint_count": 0,
            }

    client = CapturingClient()
    analyzer = BatchAnalyzer.__new__(BatchAnalyzer)
    analyzer.minimax_client = client
    analyzer.deepseek_client = None
    analyzer.rate_limiter = SimpleNamespace(wait=lambda: None)

    analyzer.analyze_single_buyer(
        "buyer",
        [
            {"sender_nick": "service", "content": "已经为您解释"},
            {"sender_nick": "buyer", "content": "是正品吗"},
            {"sender_nick": "service", "content": "您好"},
            {"sender_nick": "buyer", "content": "收到商品了"},
        ],
    )

    assert client.messages == [
        "[买家] 收到商品了",
        "[客服] 您好",
        "[买家] 是正品吗",
        "[客服] 已经为您解释",
    ]


def test_sentiment_prompt_requires_contextual_basis_not_keyword_matching():
    prompt = build_sentiment_intent_prompt(
        ["[买家] 我怀疑是假货", "[客服] 本店为官方旗舰店，所售均为正品"]
    )

    assert "sentiment_basis" in prompt
    assert "authenticity_concern" in prompt
    assert "我怀疑是假货" in prompt
    assert "不得仅因出现" in prompt
    assert "[客服] 本店为官方旗舰店" in prompt


def test_sentiment_prompt_does_not_accumulate_friction_into_negative():
    prompt = build_sentiment_intent_prompt(
        ["[买家] 你怎么听不懂", "[买家] 我等的很焦虑", "[买家] 虚假宣传吗"]
    )

    assert "多个未达到 Negative 门槛的表达不能累加升级" in prompt
    assert '"虚假宣传吗"' in prompt
    assert '"我等的很焦虑"' in prompt
    assert '"你怎么听不懂"' in prompt
    assert '"我真的会投诉你们"' in prompt
