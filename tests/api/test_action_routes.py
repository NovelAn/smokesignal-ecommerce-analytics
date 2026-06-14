"""Tests for Action API routes — inventory inquiry endpoints.

v2 routes surfacing customers whose dominant or significant intent is
inventory inquiry, so ops can act on stocking / restock demand.
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
