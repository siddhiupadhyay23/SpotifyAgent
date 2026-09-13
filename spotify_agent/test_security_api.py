"""Focused authentication and authorization verification for the local demo."""

import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SPOTIFY_AGENT_ADMIN_EMAIL", "security-admin@spotifyagent.local")
os.environ.setdefault("SPOTIFY_AGENT_ADMIN_PASSWORD", "security-test-admin-password")

from fastapi.testclient import TestClient
from api import app
import db


def create_customer(client: TestClient, name: str):
    response = client.post("/users", json={"name": name, "email": f"{name.lower().replace(' ', '.')}@example.com"})
    assert response.status_code == 201, response.text
    user = response.json()
    return user, {"Authorization": f"Bearer {user['access_token']}"}


def run_tests():
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:8]

    # A/B: credentials are verified server-side, not simply accepted by React.
    invalid = client.post("/admin/login", json={"email": os.environ["SPOTIFY_AGENT_ADMIN_EMAIL"], "password": "wrong-password"})
    assert invalid.status_code == 401, invalid.text
    admin_login = client.post("/admin/login", json={"email": os.environ["SPOTIFY_AGENT_ADMIN_EMAIL"], "password": os.environ["SPOTIFY_AGENT_ADMIN_PASSWORD"]})
    assert admin_login.status_code == 200, admin_login.text
    assert admin_login.json()["role"] == "admin"
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    admin_token = admin_login.json()["access_token"]

    # Route surface is intentionally small: interactive docs/schema are disabled
    # and no file/debug routes are registered.
    routes = {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())}
    assert ("/admin/conversations", "GET") in routes
    assert ("/conversations/{conversation_id}/admin-messages", "POST") in routes
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/.env").status_code == 404
    assert client.get("/data/support.db").status_code == 404
    assert client.get("/admin").status_code == 404
    assert client.post("/admin/conversations").status_code == 405

    # C: admin endpoints reject a missing bearer session.
    assert client.get("/admin/conversations").status_code == 401
    assert client.get(f"/conversations/missing_{suffix}").status_code == 401
    assert client.post(f"/conversations/missing_{suffix}/admin-messages", json={"content": "reply"}).status_code == 401
    assert client.patch(f"/conversations/missing_{suffix}/status", json={"status": "resolved"}).status_code == 401

    # Invalid, malformed, forged, and modified tokens never authenticate.
    for headers in (
        {"Authorization": "Bearer invalid"},
        {"Authorization": "Token invalid"},
        {"Authorization": f"Bearer {admin_token[:-1]}x"},
        {"Authorization": "Bearer " + "x" * 64},
    ):
        assert client.get("/admin/conversations", headers=headers).status_code == 401

    customer_a, customer_a_headers = create_customer(client, f"Security Customer A {suffix}")
    customer_b, customer_b_headers = create_customer(client, f"Security Customer B {suffix}")
    conversation_id = f"security_conversation_{suffix}"
    created = client.post("/conversations", json={"id": conversation_id, "user_id": customer_a["id"]}, headers=customer_a_headers)
    assert created.status_code == 201, created.text

    # D: a customer session cannot act as an admin.
    assert client.get("/admin/conversations", headers=customer_a_headers).status_code == 403
    assert client.post(f"/conversations/{conversation_id}/admin-messages", json={"content": "not an admin"}, headers=customer_a_headers).status_code == 403
    assert client.patch(f"/conversations/{conversation_id}/status", json={"status": "resolved"}, headers=customer_a_headers).status_code == 403

    # E/F/G: BOLA checks and customer sender/status restrictions.
    assert client.get(f"/conversations/{conversation_id}", headers=customer_b_headers).status_code == 403
    assert client.get(f"/users/{customer_a['id']}/conversations", headers=customer_b_headers).status_code == 403
    assert client.post(f"/conversations/{conversation_id}/messages", json={"content": "I am admin", "sender": "admin"}, headers=customer_a_headers).status_code == 403
    assert client.post("/conversations", json={"user_id": customer_a["id"], "status": "resolved"}, headers=customer_a_headers).status_code == 422

    # SQL injection probes are data, never SQL: they cannot broaden an identity
    # lookup or alter tables/records. This includes a harmless DROP-shaped string.
    user_count_before = len(client.get("/admin/conversations", headers=admin_headers).json())
    injection_values = ["'", '"', "' OR '1'='1", '" OR "1"="1', "' OR 1=1 --", "'; DROP TABLE users; --", "' UNION SELECT NULL --", "admin'--"]
    for probe in injection_values:
        result = client.post("/admin/login", json={"email": f"{probe}@example.com", "password": probe})
        assert result.status_code in (401, 422), result.text
    injected_user = client.post("/users", json={"name": "'; DROP TABLE users; --", "email": f"sql-{suffix}@example.com"})
    assert injected_user.status_code == 201, injected_user.text
    assert client.get("/admin/conversations", headers=admin_headers).status_code == 200
    assert len(client.get("/admin/conversations", headers=admin_headers).json()) == user_count_before
    assert client.get(f"/conversations/'%20OR%201=1%20--", headers=customer_a_headers).status_code == 404

    # H/I/J/K: real customer data travels through the same SQLite record and the
    # unchanged agent decisions are visible only to the authenticated admin.
    charge = client.post(f"/conversations/{conversation_id}/messages", json={"content": "I don't recognize this charge on my card.", "sender": "customer"}, headers=customer_a_headers)
    assert charge.status_code == 200, charge.text
    customer_detail = client.get(f"/conversations/{conversation_id}", headers=customer_a_headers)
    assert customer_detail.status_code == 200
    assert "agent_decisions" not in customer_detail.json()
    assert all("decision" not in message for message in customer_detail.json()["messages"])
    assert client.get(f"/conversations/..%2F..%2F.env", headers=customer_a_headers).status_code in (404, 422)

    inbox = client.get("/admin/conversations", headers=admin_headers)
    assert inbox.status_code == 200
    assert any(item["id"] == conversation_id and item["customer_id"] == customer_a["id"] for item in inbox.json())
    admin_detail = client.get(f"/conversations/{conversation_id}", headers=admin_headers).json()
    assert admin_detail["agent_decisions"][-1]["intent"] == "billing_charge"
    assert admin_detail["agent_decisions"][-1]["decision"] == "ESCALATE"
    assert "suspicious_billing" in admin_detail["agent_decisions"][-1]["escalation_reason"]

    reply = client.post(f"/conversations/{conversation_id}/admin-messages", json={"content": "A specialist is reviewing this charge."}, headers=admin_headers)
    assert reply.status_code == 201 and reply.json()["sender"] == "admin"
    resolved = client.patch(f"/conversations/{conversation_id}/status", json={"status": "resolved"}, headers=admin_headers)
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"
    reopened = client.patch(f"/conversations/{conversation_id}/status", json={"status": "open"}, headers=admin_headers)
    assert reopened.status_code == 200 and reopened.json()["status"] == "open"

    auto_id = f"security_auto_{suffix}"
    assert client.post("/conversations", json={"id": auto_id, "user_id": customer_a["id"]}, headers=customer_a_headers).status_code == 201
    auto = client.post(f"/conversations/{auto_id}/messages", json={"content": "Spotify keeps pausing on my Android phone.", "sender": "customer"}, headers=customer_a_headers)
    assert auto.status_code == 200, auto.text
    auto_detail = client.get(f"/conversations/{auto_id}", headers=admin_headers).json()
    assert auto_detail["agent_decisions"][-1]["intent"] == "device_platform"
    assert auto_detail["agent_decisions"][-1]["platform"] == "android"
    assert auto_detail["agent_decisions"][-1]["decision"] == "AUTO_HANDLE"

    # A session is opaque: SQLite has only its hash, expiry is validated, and
    # logout prevents replay. No raw session token should be persisted.
    conn = db.get_db_connection()
    try:
        stored_hash = conn.execute("SELECT token_hash FROM auth_sessions WHERE user_id = ?", (admin_login.json()["id"],)).fetchone()[0]
        assert stored_hash != admin_token and len(stored_hash) == 64
    finally:
        conn.close()
    expired_token = db.create_session(admin_login.json()["id"], ttl_hours=-1)
    assert client.get("/admin/conversations", headers={"Authorization": f"Bearer {expired_token}"}).status_code == 401
    assert client.post("/auth/logout", headers=admin_headers).status_code == 204
    assert client.get("/admin/conversations", headers=admin_headers).status_code == 401

    # Controlled validation and error paths do not disclose server internals.
    malformed = [
        client.post("/users", json={"name": "", "email": "bad"}),
        client.post("/users", json={"name": "x" * 121, "email": "valid@example.com"}),
        client.post("/users", json={"name": "Valid", "email": "x" * 250 + "@e.com"}),
        client.post("/users", json={"name": None, "email": None}),
        client.post("/users", json={"name": 42, "email": []}),
        client.post(f"/conversations/{conversation_id}/messages", json={"content": "x" * 5001}, headers=customer_a_headers),
        client.patch(f"/conversations/{conversation_id}/status", json={"status": "invalid"}, headers=customer_a_headers),
    ]
    for response in malformed:
        assert 400 <= response.status_code < 500, response.text
        body = response.text.lower()
        assert "traceback" not in body and "select " not in body and "c:\\users" not in body
    health = client.get("/health")
    assert health.status_code == 200 and "db_path" not in health.json()

    # CORS only grants the configured local frontend and never bypasses auth.
    allowed = client.options("/admin/conversations", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    blocked = client.options("/admin/conversations", headers={"Origin": "https://attacker.invalid", "Access-Control-Request-Method": "GET"})
    assert blocked.headers.get("access-control-allow-origin") is None
    assert client.get("/admin/conversations", headers={"Origin": "https://attacker.invalid"}).status_code == 401

    print("Penetration-style security API test passed")


if __name__ == "__main__":
    run_tests()
