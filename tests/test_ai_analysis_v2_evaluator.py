from datetime import datetime
from types import SimpleNamespace

import scripts.evaluate_ai_v2_gold as evaluator


def test_recheck_corrected_replaces_only_corrected_model_payload(monkeypatch):
    start = datetime(2026, 1, 1, 10)
    end = datetime(2026, 1, 1, 11)
    replacement = {"events": [{"sentiment_label": "Neutral"}]}

    class Repository:
        def load_source(self, buyer_nick, mode):
            return SimpleNamespace(chats=[], profile={})

    class Analyzer:
        PROMPT_VERSION = "test"

        def __init__(self, repository):
            pass

        def _analyze_window(self, window, open_events, profile, customer_state):
            payload = SimpleNamespace(model_dump=lambda mode: replacement)
            return SimpleNamespace(payload=payload)

    window = SimpleNamespace(
        source_from_msg_time=start,
        source_to_msg_time=end,
    )
    monkeypatch.setattr(evaluator, "AIAnalysisV2Repository", Repository)
    monkeypatch.setattr(evaluator, "AIAnalysisV2Analyzer", Analyzer)
    monkeypatch.setattr(evaluator, "prepare_windows", lambda *args, **kwargs: [window])
    rows = [
        {
            "review_status": "corrected",
            "buyer_nick": "buyer",
            "event_started_at": start,
            "event_ended_at": end,
            "model_payload": {"events": []},
        },
        {"review_status": "approved", "model_payload": {"events": ["original"]}},
    ]

    result, count = evaluator.recheck_corrected(rows)

    assert count == 1
    assert result[0]["model_payload"] == replacement
    assert result[1]["model_payload"] == {"events": ["original"]}
