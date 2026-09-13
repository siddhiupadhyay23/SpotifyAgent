"""
Test script for Phase 1: Real Backend + SQLite.
Tests all endpoints and verifies persistence in SQLite for arbitrary customer messages.
"""
import sys
import json
import sqlite3
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from api import app
import db


def run_tests():
    print("=================================================================")
    print("PHASE 1 VERIFICATION — SPOTIFYAGENT FASTAPI + SQLITE")
    print("=================================================================")

    client = TestClient(app)

    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    print("\n[1/7] GET /health")
    print("      Response:", res.json())

    # 2. Create User
    user_payload = {
        "name": "Siddharth Rao",
        "email": "siddharth@example.com",
        "role": "customer",
    }
    user_res = client.post("/users", json=user_payload)
    assert user_res.status_code == 201, f"User creation failed: {user_res.status_code} {user_res.text}"
    user = user_res.json()
    user_id = user["id"]
    print(f"\n[2/7] POST /users -> Created user ID: {user_id}")
    print(f"      Data: {user}")

    # 3. Create Conversation
    conv_payload = {
        "user_id": user_id,
        "status": "open",
    }
    conv_res = client.post("/conversations", json=conv_payload)
    assert conv_res.status_code == 201, f"Conv creation failed: {conv_res.status_code} {conv_res.text}"
    conv = conv_res.json()
    conv_id = conv["id"]
    print(f"\n[3/7] POST /conversations -> Created conversation ID: {conv_id}")
    print(f"      Data: {conv}")

    # 4. Test 3 Arbitrary Customer Messages
    test_messages = [
        {
            "category": "Playback / Device Issue",
            "text": "The Spotify app on my Android phone keeps pausing tracks randomly every two minutes.",
            "expected_intent": "playback_error",
        },
        {
            "category": "Billing / Charge Issue",
            "text": "I noticed an unauthorized charge of $10.99 on my credit card statement for Spotify and need a refund.",
            "expected_intent": "billing_charge",
        },
        {
            "category": "Login / Account Issue",
            "text": "I forgot my password and cannot log in to my account on desktop.",
            "expected_intent": "account_login",
        },
    ]

    print("\n[4/7] POST /conversations/{conversation_id}/messages (Processing 3 Test Messages)")
    for i, item in enumerate(test_messages, 1):
        payload = {"content": item["text"]}
        msg_res = client.post(f"/conversations/{conv_id}/messages", json=payload)
        assert msg_res.status_code == 200, f"Message {i} failed: {msg_res.status_code} {msg_res.text}"
        data = msg_res.json()

        print(f"\n  -- Message {i}: {item['category']} --")
        print(f"  Customer Message  : \"{data['message']}\"")
        print(f"  Classified Intent : {data['intent']} (Confidence: {data['confidence']:.2%})")
        print(f"  Platform Detected : {data['platform']}")
        print(f"  Escalation Policy : {data['decision']}")
        print(f"  Escalation Reason : {data['escalation_reason']}")
        print(f"  Agent Response    : \"{data['response']}\"")
        print(f"  Evidence Count    : {len(data.get('retrieved_evidence', []))} pairs retrieved")
        print(f"  Saved Message IDs : Customer={data['customer_message_id']}, Agent={data['agent_message_id']}")
        print(f"  Decision DB ID    : {data['agent_decision_id']}")

    # 5. Retrieve Conversation Details
    print(f"\n[5/7] GET /conversations/{conv_id}")
    get_conv = client.get(f"/conversations/{conv_id}")
    assert get_conv.status_code == 200, f"Get conv failed: {get_conv.status_code}"
    c_data = get_conv.json()
    print(f"      Conversation status : {c_data['status']}")
    print(f"      Total messages in DB: {len(c_data['messages'])} (3 customer + 3 agent)")
    print(f"      Total decisions in DB: {len(c_data['agent_decisions'])}")
    assert len(c_data["messages"]) == 6, f"Expected 6 messages, got {len(c_data['messages'])}"
    assert len(c_data["agent_decisions"]) == 3, f"Expected 3 decisions, got {len(c_data['agent_decisions'])}"

    # 6. Direct SQLite Database Inspection
    print(f"\n[6/7] Direct SQLite Table Inspection ({db.DB_PATH})")
    conn = sqlite3.connect(str(db.DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    users_count = cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    convs_count = cursor.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    msgs_count = cursor.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    decs_count = cursor.execute("SELECT COUNT(*) FROM agent_decisions").fetchone()[0]

    print(f"      users table rows           : {users_count}")
    print(f"      conversations table rows   : {convs_count}")
    print(f"      messages table rows        : {msgs_count}")
    print(f"      agent_decisions table rows : {decs_count}")

    # Inspect decision rows in detail
    dec_rows = cursor.execute(
        "SELECT id, message_id, intent, confidence, platform, decision, escalation_reason, response, retrieval_evidence, created_at "
        "FROM agent_decisions ORDER BY created_at ASC"
    ).fetchall()

    for idx, d in enumerate(dec_rows, 1):
        ev = json.loads(d["retrieval_evidence"])
        print(f"      Decision {idx}: Intent={d['intent']}, Conf={d['confidence']:.2f}, Decision={d['decision']}, EvidenceLen={len(ev)}")

    conn.close()

    # 7. Backward compatibility check
    print("\n[7/8] Backward Compatibility Check (POST /predict)")
    pred_res = client.post("/predict", json={"message": "Cannot download playlists for offline listening on iOS"})
    assert pred_res.status_code == 200
    pred_data = pred_res.json()
    print(f"      Intent: {pred_data['intent']} | Platform: {pred_data['platform']} | Decision: {pred_data['decision']}")
    print("      Existing /predict endpoint continues to function without disruption.")

    # 8. Required Safety and Presentation Cases
    print("\n[8/8] Safety & Presentation Verification Cases (POST /conversations/{conversation_id}/messages)")
    safety_cases = [
        ("a", "I was charged twice for Premium"),
        ("b", "I don't recognize this charge on my card"),
        ("c", "My account was hacked"),
        ("d", "Spotify keeps pausing on Android"),
    ]

    for code, text in safety_cases:
        m_res = client.post(f"/conversations/{conv_id}/messages", json={"content": text})
        assert m_res.status_code == 200, f"Case {code} failed: {m_res.status_code}"
        d = m_res.json()
        print(f"\n  Case {code}) \"{text}\"")
        print(f"    Intent    : {d['intent']}")
        print(f"    Confidence: {d['confidence']:.4f}")
        print(f"    Platform  : {d['platform']}")
        print(f"    Decision  : {d['decision']}")
        print(f"    Reason    : {d['escalation_reason']}")
        print(f"    Response  : {d['response']}")

        # Verify assertions:
        # The duplicate-charge case preserves the pre-existing billing-dispute policy.
        # Unauthorized billing and account compromise must always escalate.
        if code in ["a", "b", "c"]:
            assert d["decision"] == "ESCALATE", f"Expected ESCALATE for case {code}, got {d['decision']}"
        # Case d should be auto-handled
        if code == "d":
            assert d["decision"] == "AUTO_HANDLE", f"Expected AUTO_HANDLE for case {code}, got {d['decision']}"

        # Presentation checks:
        assert "Peter" not in d["response"], f"Found customer name 'Peter' in response: {d['response']}"
        assert "t.co" not in d["response"], f"Found shortened URL in response: {d['response']}"

    # Direct sanitization check for the historical Twitter formats that may appear in evidence.
    from agent import _clean_response
    cleaned = _clean_response("Hey Peter! Try restarting Spotify. [help](https://t.co/abc)")
    assert "Peter" not in cleaned, f"Historical name was not removed: {cleaned}"
    assert "t.co" not in cleaned, f"Historical t.co URL was not removed: {cleaned}"


    print("\n=================================================================")
    print("ALL PHASE 1 BACKEND + SQLITE REQUIREMENTS VERIFIED SUCCESSFULLY!")
    print("=================================================================")


if __name__ == "__main__":
    run_tests()
