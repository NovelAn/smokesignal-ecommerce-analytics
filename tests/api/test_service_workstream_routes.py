import asyncio

from backend.api import target_routes


class FakeAnalyzer:
    def __init__(self):
        self.calls = []

    def get_service_history(self, buyer_nick, workstream="priority"):
        self.calls.append(("history", buyer_nick, workstream))
        return [{"status": "pending"}]

    def mark_service(self, buyer_nick, status, notes=None, workstream="priority"):
        self.calls.append(("mark", buyer_nick, status, notes, workstream))
        return 1


def test_service_mark_defaults_to_priority(monkeypatch):
    fake = FakeAnalyzer()
    monkeypatch.setattr(target_routes, "analyzer", fake)

    response = asyncio.run(target_routes.mark_customer_service(
        target_routes.ServiceMarkRequest(buyer_nick="buyer-a", status="contacted")
    ))

    assert response.workstream == "priority"
    assert ("mark", "buyer-a", "contacted", None, "priority") in fake.calls


def test_service_mark_supports_inventory_workstream(monkeypatch):
    fake = FakeAnalyzer()
    monkeypatch.setattr(target_routes, "analyzer", fake)

    response = asyncio.run(target_routes.mark_customer_service(
        target_routes.ServiceMarkRequest(
            buyer_nick="buyer-b",
            status="resolved",
            workstream="inventory",
        )
    ))

    assert response.workstream == "inventory"
    assert ("mark", "buyer-b", "resolved", None, "inventory") in fake.calls
