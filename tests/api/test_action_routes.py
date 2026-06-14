"""Tests for Action API routes — inventory inquiry endpoints.

v2 route surfacing customers who have ANY inventory need:
  - AI primary: intent_distribution['Inventory Inquiry'] > 0 (not restricted to dominant_intent)
  - keyword fallback: chat_history buyer messages hit inventory keywords
so ops can act on stocking / restock demand, with the actual questions shown.
"""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_inventory_inquiries():
    response = client.get("/api/v2/action/inventory-inquiries")
    assert response.status_code == 200
    data = response.json()
    assert "inquiries" in data
    assert "total_count" in data
    assert isinstance(data["inquiries"], list)
    assert data["total_count"] == len(data["inquiries"])


def test_inventory_inquiry_fields():
    """每条记录含必要字段，包括具体提问与来源标记"""
    response = client.get("/api/v2/action/inventory-inquiries")
    assert response.status_code == 200
    data = response.json()
    if not data["inquiries"]:
        return  # 无数据时跳过结构断言
    first = data["inquiries"][0]
    for field in (
        "buyer_nick", "vip_level", "inventory_questions", "question_count",
        "last_inventory_msg_time", "dominant_intent", "intent_distribution",
        "sentiment_label", "detected_by",
    ):
        assert field in first, f"missing field: {field}"
    assert isinstance(first["inventory_questions"], list)
    assert first["detected_by"] in ("ai", "keyword", "both")
    # 关键词来源的记录应有提问原文；ai-only 可能无（兜底未命中关键词）
    if first["detected_by"] in ("keyword", "both"):
        assert first["question_count"] >= 1


def test_inventory_not_restricted_to_dominant_intent():
    """纳入标准不限于 dominant_intent='Inventory Inquiry'——
    只要 intent_distribution 有库存意图或关键词命中即可。
    用真实数据验证：列表里应存在 dominant_intent 不是 Inventory Inquiry 的客户。
    """
    response = client.get("/api/v2/action/inventory-inquiries")
    data = response.json()
    if not data["inquiries"]:
        return
    non_inventory_dominant = [
        q for q in data["inquiries"] if q["dominant_intent"] != "Inventory Inquiry"
    ]
    # 真实库中应至少有一个「主导意图非库存、但问了库存」的客户（关键词兜底路径）
    assert len(non_inventory_dominant) >= 1, "expected buyers with inventory need but non-inventory dominant intent"
