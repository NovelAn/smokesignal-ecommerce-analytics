"""
Overview 改造 - 4 个活跃 API 的端到端测试

覆盖：
- dashboard 概览工作流（vic-persona → period-comparison → customer-trends → inventory-inquiries）
- 返回数据类型一致性
- 性能（4 个活跃 API 合计 < 5s）

注意：依赖真实 DB（aliyunDB），从本机直连可通。
"""
import time

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_dashboard_overview_apis_workflow():
    """验证 4 个活跃 API 的完整工作流"""
    # 1. VIC 群体画像
    response = client.get("/api/v2/insights/vic-persona")
    assert response.status_code == 200
    vic_data = response.json()
    assert vic_data["total_vic_count"] >= 0

    # 2. 时间对比（当期 5 月 → 对比期 4 月）
    response = client.get(
        "/api/v2/insights/period-comparison",
        params={"start_date": "2026-05-01", "end_date": "2026-05-31"},
    )
    assert response.status_code == 200
    comparison = response.json()
    assert "current_period" in comparison
    assert comparison["current_period"]["start_date"] == "2026-05-01"
    assert comparison["comparison_period"]["end_date"] == "2026-04-30"

    # 3. 客户趋势
    response = client.get("/api/v2/insights/customer-trends?months=6")
    assert response.status_code == 200
    trends = response.json()
    assert "vic_pool_trend" in trends

    # 4. 库存需求
    response = client.get("/api/v2/action/inventory-inquiries")
    assert response.status_code == 200
    inventory = response.json()
    assert "inquiries" in inventory


def test_apis_return_consistent_data_types():
    """验证返回数据类型一致性"""
    response = client.get("/api/v2/insights/vic-persona")
    data = response.json()
    assert isinstance(data["total_vic_count"], int)
    assert isinstance(data["key_interests"], list)
    assert isinstance(data["key_pain_points"], list)
    if len(data["key_interests"]) > 0:
        first = data["key_interests"][0]
        assert isinstance(first["keyword"], str)
        assert isinstance(first["count"], int)
        assert isinstance(first["percentage"], (int, float))


def test_apis_performance_under_5s():
    """验证 5 个新 API 合计响应 < 5s"""
    endpoints = [
        "/api/v2/insights/vic-persona",
        "/api/v2/insights/period-comparison?start_date=2026-05-01&end_date=2026-05-31",
        "/api/v2/insights/customer-trends?months=6",
        "/api/v2/action/inventory-inquiries",
    ]
    start = time.time()
    for url in endpoints:
        r = client.get(url)
        assert r.status_code == 200
    elapsed = time.time() - start
    print(f"\n4 APIs total: {elapsed:.2f}s")
    assert elapsed < 5.0
