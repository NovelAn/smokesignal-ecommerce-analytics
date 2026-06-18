from datetime import datetime

from backend.analytics.keyword_analyzer import KeywordAnalyzer


def test_keyword_analyzer_uses_one_message_basis_for_all_categories():
    analyzer = KeywordAnalyzer()
    rows = [
        {"content": "这件外套还有库存吗", "msg_time": datetime(2026, 6, 10, 10, 0)},
        {"content": "有没有优惠券和赠品", "msg_time": datetime(2026, 6, 11, 10, 0)},
        {"content": "什么时候发货", "msg_time": datetime(2026, 6, 12, 10, 0)},
    ]

    result = analyzer.analyze_messages(rows, limit=20)

    counts = {item["name"]: item["value"] for item in result["category_distribution"]}
    assert counts["库存查询"] == 1
    assert counts["价格"] == 1
    assert counts["物流"] == 1
    assert result["total_messages"] == 3
    assert result["last_message_at"] == "2026-06-12T10:00:00"


def test_keyword_analyzer_category_filter_only_returns_matching_keywords():
    analyzer = KeywordAnalyzer()
    rows = [
        {"content": "还有库存吗", "msg_time": datetime(2026, 6, 10, 10, 0)},
        {"content": "优惠券怎么领取", "msg_time": datetime(2026, 6, 11, 10, 0)},
    ]

    result = analyzer.analyze_messages(rows, category="库存查询", limit=20)

    assert result["keywords"]
    assert {item["category"] for item in result["keywords"]} == {"库存查询"}
