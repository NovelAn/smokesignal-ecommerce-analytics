"""Integration tests for Insights API routes (Task 8).

These tests hit the real DB via the analytics classes wired into the
insights router. They use FastAPI's TestClient against `backend.main:app`.
"""
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_vic_persona():
    response = client.get("/api/v2/insights/vic-persona")
    assert response.status_code == 200
    data = response.json()
    assert "total_vic_count" in data
    assert "key_interests" in data
    assert "key_pain_points" in data
    assert "purchase_motivations" in data


def test_get_period_comparison_invalid_date():
    response = client.get(
        "/api/v2/insights/period-comparison?start_date=2026-12-01&end_date=2026-11-01"
    )
    assert response.status_code == 400


def test_get_customer_trends_default():
    response = client.get("/api/v2/insights/customer-trends")
    assert response.status_code == 200
    data = response.json()
    assert "vic_pool_trend" in data


def test_get_customer_trends_custom_months():
    response = client.get("/api/v2/insights/customer-trends?months=3")
    assert response.status_code == 200


def test_get_anomaly_alerts():
    response = client.get("/api/v2/insights/anomaly-alerts")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    assert "total_count" in data


def test_anomaly_alerts_is_marked_deprecated_in_openapi():
    operation = app.openapi()["paths"]["/api/v2/insights/anomaly-alerts"]["get"]
    assert operation["deprecated"] is True
