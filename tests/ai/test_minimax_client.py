"""
MiniMax client parsing tests.
"""
from backend.ai.minimax_client import MiniMaxClient


def make_client():
    return MiniMaxClient.__new__(MiniMaxClient)


def test_parse_sentiment_response_with_thinking_and_markdown():
    client = make_client()
    response = """
<think>先逐条判断情绪。</think>
```json
[
  {"score": 0.5, "sentiment": "Neutral"},
  {"score": 0.2, "sentiment": "Negative"}
]
```
"""

    result = client._parse_sentiment_response(response, 2)

    assert result == [
        {"score": 0.5, "sentiment": "Neutral", "_parse_failed": False},
        {"score": 0.2, "sentiment": "Negative", "_parse_failed": False},
    ]


def test_parse_sentiment_response_accepts_real_all_neutral():
    client = make_client()
    response = '结果如下：[{"score": 0.5, "sentiment": "Neutral"}]'

    result = client._parse_sentiment_response(response, 1)

    assert result == [
        {"score": 0.5, "sentiment": "Neutral", "_parse_failed": False}
    ]


def test_parse_sentiment_response_marks_parse_failure():
    client = make_client()

    result = client._parse_sentiment_response("无法判断", 2)

    assert result == [
        {"score": 0.5, "sentiment": "Neutral", "_parse_failed": True},
        {"score": 0.5, "sentiment": "Neutral", "_parse_failed": True},
    ]


def test_parse_intent_response_with_surrounding_text():
    client = make_client()
    response = """
分析完成：
{
  "Pre-sale Inquiry": 2,
  "Post-sale Support": 1,
  "Logistics": 0,
  "Usage Guide": 0,
  "Complaint": 0
}
"""

    result = client._parse_intent_response(response)

    assert result == {
        "Pre-sale Inquiry": 2,
        "Post-sale Support": 1,
        "Logistics": 0,
        "Usage Guide": 0,
        "Complaint": 0,
        "_parse_failed": False,
    }


def test_parse_intent_response_marks_parse_failure():
    client = make_client()

    result = client._parse_intent_response("不是JSON")

    assert result == {
        "Pre-sale Inquiry": 0,
        "Post-sale Support": 0,
        "Logistics": 0,
        "Usage Guide": 0,
        "Complaint": 0,
        "_parse_failed": True,
    }
