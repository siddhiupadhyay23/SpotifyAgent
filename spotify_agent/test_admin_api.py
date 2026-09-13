"""End-to-end verification for the Phase 3 admin support workflow."""

import sys
import os
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SPOTIFY_AGENT_ADMIN_EMAIL", "admin-test@spotifyagent.local")
os.environ.setdefault("SPOTIFY_AGENT_ADMIN_PASSWORD", "local-test-admin-password")

from fastapi.testclient import TestClient
from api import app


def run_tests():
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:8]
    customer_id = f"phase3_customer_{suffix}"
    escalated_id = f"phase3_escalated_{suffix}"
    auto_id = f"phase3_auto_{suffix}"

    # Local/demo admin access reuses the users table and admin role.
    admin = client.post("/admin/login", json={"email": os.environ["SPOTIFY_AGENT_ADMIN_EMAIL"], "password": os.environ["SPOTIFY_AGENT_ADMIN_PASSWORD"]})
    assert admin.status_code == 200, admin.text
    assert admin.json()["role"] == "admin"
    admin_headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}

    customer = client.post("/users", json={"name": "Phase 3 Customer", "email": "customer-phase3@example.com"})
    assert customer.status_code == 201, customer.text
    customer_id = customer.json()["id"]
    customer_headers = {"Authorization": f"Bearer {customer.json()['access_token']}"}

    for conversation_id in (escalated_id, auto_id):
        created = client.post("/conversations", json={"id": conversation_id, "user_id": customer_id}, headers=customer_headers)
        assert created.status_code == 201, created.text

    # Customer request runs the real pipeline and changes the workflow state.
    escalated = client.post(
        f"/conversations/{escalated_id}/messages",
        json={"content": "I don't recognize this charge on my card.", "sender": "customer"}, headers=customer_headers,
    )
    assert escalated.status_code == 200, escalated.text
    assert escalated.json()["response"], escalated.json()

    inbox = client.get("/admin/conversations", headers=admin_headers)
    assert inbox.status_code == 200, inbox.text
    escalated_summary = next(item for item in inbox.json() if item["id"] == escalated_id)
    assert escalated_summary["customer_name"] == "Phase 3 Customer"
    assert escalated_summary["has_escalation"] is True
    assert escalated_summary["status"] == "escalated"
    assert escalated_summary["message_count"] == 2

    detail = client.get(f"/conversations/{escalated_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    detail_json = detail.json()
    assert [message["sender"] for message in detail_json["messages"]] == ["customer", "agent"]
    decision = detail_json["agent_decisions"][0]
    assert decision["intent"] == "billing_charge"
    assert decision["decision"] == "ESCALATE"
    assert decision["escalation_reason"]
    decision_count = len(detail_json["agent_decisions"])

    # Human takeover persists a message and does not invoke or add an AI decision.
    human_reply = "Hi, I've reviewed your case and will help you with the charge."
    admin_reply = client.post(f"/conversations/{escalated_id}/admin-messages", json={"content": human_reply}, headers=admin_headers)
    assert admin_reply.status_code == 201, admin_reply.text
    assert admin_reply.json()["sender"] == "admin"

    after_admin_reply = client.get(f"/conversations/{escalated_id}", headers=admin_headers).json()
    assert after_admin_reply["messages"][-1]["sender"] == "admin"
    assert after_admin_reply["messages"][-1]["content"] == human_reply
    assert len(after_admin_reply["agent_decisions"]) == decision_count

    resolved = client.patch(f"/conversations/{escalated_id}/status", json={"status": "resolved"}, headers=admin_headers)
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert client.get(f"/conversations/{escalated_id}", headers=customer_headers).json()["status"] == "resolved"
    assert any(item["id"] == escalated_id and item["status"] == "resolved" for item in client.get("/admin/conversations", headers=admin_headers).json())

    # The customer list is a summary; full customer refresh exposes the human reply.
    refreshed_customer_thread = client.get(f"/conversations/{escalated_id}", headers=customer_headers).json()
    assert any(message["sender"] == "admin" and message["content"] == human_reply for message in refreshed_customer_thread["messages"])

    auto_handled = client.post(
        f"/conversations/{auto_id}/messages",
        json={"content": "Spotify keeps pausing on Android.", "sender": "customer"}, headers=customer_headers,
    )
    assert auto_handled.status_code == 200, auto_handled.text
    auto_detail = client.get(f"/conversations/{auto_id}", headers=admin_headers).json()
    assert auto_detail["agent_decisions"][-1]["decision"] == "AUTO_HANDLE", auto_detail
    auto_summary = next(item for item in client.get("/admin/conversations", headers=admin_headers).json() if item["id"] == auto_id)
    assert auto_summary["status"] == "open"
    assert auto_summary["has_escalation"] is False

    print("Phase 3 admin support end-to-end test passed")


if __name__ == "__main__":
    run_tests()
