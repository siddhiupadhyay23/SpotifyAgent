"""
Database layer for SpotifyAgent using Python's built-in sqlite3.

Manages tables:
- users (id, name, email, role)
- conversations (id, user_id, status, created_at, updated_at)
- messages (id, conversation_id, sender, content, created_at)
- agent_decisions (id, message_id, intent, confidence, platform, decision, escalation_reason, response, retrieval_evidence, created_at)
"""

import os
import json
import sqlite3
import uuid
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("SPOTIFY_AGENT_DB_PATH", str(DATA_DIR / "support.db")))


def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe sqlite3 connection."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create all required tables if they do not exist."""
    conn = get_db_connection()
    try:
        with conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer'
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agent_decisions (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                intent TEXT NOT NULL,
                confidence REAL NOT NULL,
                platform TEXT NOT NULL,
                decision TEXT NOT NULL,
                escalation_reason TEXT,
                response TEXT NOT NULL,
                retrieval_evidence TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_message ON agent_decisions(message_id);
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);
            """)
    finally:
        conn.close()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Users ────────────────────────────────────────────────────────────

def create_user(name: str, email: str, role: str = "customer", user_id: Optional[str] = None) -> Dict[str, Any]:
    uid = user_id or f"usr_{uuid.uuid4().hex[:8]}"
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (id, name, email, role) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, email=excluded.email, role=excluded.role",
                (uid, name, email, role)
            )
        return {"id": uid, "name": name, "email": email, "role": role}
    finally:
        conn.close()


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def ensure_user(user_id: str, name: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
    user = get_user(user_id)
    if user:
        return user
    u_name = name or f"User {user_id}"
    u_email = email or f"{user_id}@example.com"
    return create_user(name=u_name, email=u_email, user_id=user_id)


# ── Local demo sessions ─────────────────────────────────────────────

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: str, ttl_hours: int = 8) -> str:
    """Issue an opaque bearer token while storing only its SHA-256 hash."""
    from datetime import timedelta

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now.isoformat(),))
            conn.execute(
                "INSERT INTO auth_sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (_token_hash(token), user_id, expires_at.isoformat(), now.isoformat()),
            )
        return token
    finally:
        conn.close()


def get_session_user(token: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        row = conn.execute(
            """
            SELECT u.id, u.name, u.email, u.role
            FROM auth_sessions AS s
            JOIN users AS u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (_token_hash(token), utc_now_iso()),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def revoke_session(token: str) -> None:
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_token_hash(token),))
    finally:
        conn.close()


# ── Conversations ────────────────────────────────────────────────────

def create_conversation(user_id: str, status: str = "open", conversation_id: Optional[str] = None) -> Dict[str, Any]:
    ensure_user(user_id)
    cid = conversation_id or f"conv_{uuid.uuid4().hex[:8]}"
    now = utc_now_iso()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO conversations (id, user_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (cid, user_id, status, now, now)
            )
        return {
            "id": cid,
            "user_id": user_id,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
    finally:
        conn.close()


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        c_row = conn.execute(
            "SELECT id, user_id, status, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,)
        ).fetchone()
        if not c_row:
            return None

        conv = dict(c_row)

        m_rows = conn.execute(
            "SELECT id, conversation_id, sender, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        ).fetchall()

        msg_ids = [m["id"] for m in m_rows]
        decisions_by_msg = {}
        all_decisions = []

        if msg_ids:
            placeholders = ",".join("?" for _ in msg_ids)
            d_rows = conn.execute(
                f"SELECT id, message_id, intent, confidence, platform, decision, "
                f"escalation_reason, response, retrieval_evidence, created_at "
                f"FROM agent_decisions WHERE message_id IN ({placeholders}) ORDER BY created_at ASC",
                msg_ids
            ).fetchall()

            for d in d_rows:
                d_dict = dict(d)
                try:
                    d_dict["retrieval_evidence"] = json.loads(d_dict["retrieval_evidence"] or "[]")
                except Exception:
                    pass
                decisions_by_msg[d["message_id"]] = d_dict
                all_decisions.append(d_dict)

        messages = []
        for m in m_rows:
            m_dict = dict(m)
            if m["id"] in decisions_by_msg:
                m_dict["decision"] = decisions_by_msg[m["id"]]
            messages.append(m_dict)

        conv["messages"] = messages
        conv["agent_decisions"] = all_decisions
        return conv
    finally:
        conn.close()


def list_user_conversations(user_id: str) -> List[Dict[str, Any]]:
    """Return a user's conversations, newest activity first.

    The portal only needs enough information to render its inbox. Full message and
    decision history remains available through ``get_conversation``.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.user_id,
                c.status,
                c.created_at,
                c.updated_at,
                (
                    SELECT m.content
                    FROM messages AS m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC, m.rowid DESC
                    LIMIT 1
                ) AS last_message,
                (
                    SELECT m.created_at
                    FROM messages AS m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC, m.rowid DESC
                    LIMIT 1
                ) AS last_message_at,
                (
                    SELECT COUNT(*)
                    FROM messages AS m
                    WHERE m.conversation_id = c.id
                ) AS message_count
            FROM conversations AS c
            WHERE c.user_id = ?
            ORDER BY c.updated_at DESC, c.rowid DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_admin_conversations() -> List[Dict[str, Any]]:
    """Return the real support inbox with customer and escalation summaries."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.status,
                c.created_at,
                c.updated_at,
                u.id AS customer_id,
                u.name AS customer_name,
                u.email AS customer_email,
                (
                    SELECT m.content FROM messages AS m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC, m.rowid DESC LIMIT 1
                ) AS last_message,
                (
                    SELECT m.created_at FROM messages AS m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC, m.rowid DESC LIMIT 1
                ) AS last_message_at,
                (SELECT COUNT(*) FROM messages AS m WHERE m.conversation_id = c.id) AS message_count,
                EXISTS(
                    SELECT 1
                    FROM agent_decisions AS d
                    JOIN messages AS m ON m.id = d.message_id
                    WHERE m.conversation_id = c.id AND d.decision = 'ESCALATE'
                ) AS has_escalation
            FROM conversations AS c
            JOIN users AS u ON u.id = c.user_id
            ORDER BY
                CASE WHEN c.status = 'escalated' THEN 0 ELSE 1 END,
                c.updated_at DESC,
                c.rowid DESC
            """
        ).fetchall()
        return [{**dict(row), "has_escalation": bool(row["has_escalation"])} for row in rows]
    finally:
        conn.close()


def update_conversation_status(conversation_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Set one of the supported human-support workflow statuses."""
    now = utc_now_iso()
    conn = get_db_connection()
    try:
        with conn:
            updated = conn.execute(
                "UPDATE conversations SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, conversation_id),
            ).rowcount
        if not updated:
            return None
        row = conn.execute(
            "SELECT id, user_id, status, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── Messages & Decisions ─────────────────────────────────────────────

def add_message(conversation_id: str, sender: str, content: str, message_id: Optional[str] = None) -> Dict[str, Any]:
    mid = message_id or f"msg_{uuid.uuid4().hex[:8]}"
    now = utc_now_iso()
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, sender, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (mid, conversation_id, sender, content, now)
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
        return {
            "id": mid,
            "conversation_id": conversation_id,
            "sender": sender,
            "content": content,
            "created_at": now,
        }
    finally:
        conn.close()


def add_agent_decision(
    message_id: str,
    intent: str,
    confidence: float,
    platform: str,
    decision: str,
    escalation_reason: Optional[str],
    response: str,
    retrieval_evidence: Any,
    decision_id: Optional[str] = None,
) -> Dict[str, Any]:
    did = decision_id or f"dec_{uuid.uuid4().hex[:8]}"
    now = utc_now_iso()
    ev_str = json.dumps(retrieval_evidence) if not isinstance(retrieval_evidence, str) else retrieval_evidence

    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO agent_decisions ("
                "id, message_id, intent, confidence, platform, decision, "
                "escalation_reason, response, retrieval_evidence, created_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (did, message_id, intent, confidence, platform, decision,
                 escalation_reason, response, ev_str, now)
            )
        return {
            "id": did,
            "message_id": message_id,
            "intent": intent,
            "confidence": confidence,
            "platform": platform,
            "decision": decision,
            "escalation_reason": escalation_reason,
            "response": response,
            "retrieval_evidence": retrieval_evidence,
            "created_at": now,
        }
    finally:
        conn.close()


# Ensure tables exist when db module is loaded
init_db()
