"""Shared failure contract for AI analysis and persistence."""

import json
from typing import Any, Dict


class AIAnalysisUnavailableError(RuntimeError):
    """All configured AI providers failed; the analysis must remain retryable."""


def parse_first_json_object(response_text: str) -> Dict[str, Any]:
    """Extract the first complete JSON object, ignoring surrounding model text."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(response_text or ""):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(response_text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("No complete JSON object found")


def is_explicit_failure_result(result: Dict[str, Any]) -> bool:
    """Return True for provider errors and retry placeholders, never business data."""
    if not isinstance(result, dict) or not result:
        return True

    method = str(
        result.get("analysis_method") or result.get("sentiment_method") or ""
    ).strip().lower()
    status = str(result.get("status") or "").strip().lower()

    return bool(
        result.get("error")
        or result.get("_parse_failed")
        or method in {"error", "failed", "pending_retry"}
        or status in {"error", "failed", "pending_retry"}
    )


def validate_sentiment_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize the provider sentiment/intent response schema."""
    required = {
        "sentiment_score",
        "sentiment_label",
        "intent_distribution",
        "dominant_intent",
        "complaint_count",
    }
    if not isinstance(result, dict) or required.difference(result):
        raise ValueError("Invalid sentiment/intent response schema")

    try:
        score = float(result["sentiment_score"])
        complaint_count = int(result["complaint_count"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid sentiment/intent response schema") from exc

    label = result["sentiment_label"]
    intents = result["intent_distribution"]
    dominant_intent = result["dominant_intent"]
    if (
        label not in {"Positive", "Neutral", "Negative"}
        or not 0 <= score <= 1
        or not isinstance(intents, dict)
        or not isinstance(dominant_intent, str)
        or complaint_count < 0
    ):
        raise ValueError("Invalid sentiment/intent response schema")

    return {
        "sentiment_score": score,
        "sentiment_label": label,
        "intent_distribution": intents,
        "dominant_intent": dominant_intent,
        "complaint_count": complaint_count,
    }
