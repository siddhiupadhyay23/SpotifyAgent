"""
FastAPI backend for SpotifyCares AI Support Agent.
Supports interactive customer conversations with SQLite persistence.

Run: uvicorn api:app --reload --port 8000
"""

import os
import sys
import hmac
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from contextlib import asynccontextmanager

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
from agent import run as agent_run


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database is initialized on startup."""
    db.init_db()
    yield


app = FastAPI(
    title="SpotifyCares Agent API",
    description="Interactive customer support agent with SQLite persistence.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Local browser origins only. Bearer tokens are sent explicitly, so cookies are
# not needed and wildcard origins must not be used.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ────────────────────────────────────────

class PredictRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, pattern=r".*\S.*", description="User full name or display name")
    email: str = Field(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="User email address")


class ConversationCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=120, description="User ID associated with conversation")
    status: Literal["open"] = Field("open", description="Customers may create open conversations")
    id: Optional[str] = Field(None, min_length=1, max_length=120, description="Optional custom conversation ID")


class MessageCreate(BaseModel):
    content: Optional[str] = Field(None, max_length=5000, description="Message text")
    message: Optional[str] = Field(None, max_length=5000, description="Alternative field for message text")
    text: Optional[str] = Field(None, max_length=5000, description="Alternative field for message text")
    sender: str = Field("customer", description="Customers may only send customer messages")


class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=1, max_length=256)


class AdminMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Human admin reply text")


class ConversationStatusUpdate(BaseModel):
    status: Literal["open", "escalated", "resolved"]


def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return token


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = db.get_session_user(_bearer_token(authorization))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    return user


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def _require_conversation_owner(conversation_id: str, current_user: Dict[str, Any]) -> Dict[str, Any]:
    conversation = db.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user["role"] != "admin" and conversation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conversation access denied")
    return conversation


def _customer_conversation_view(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """Exclude internal agent decision details from customer API responses."""
    return {
        key: value for key, value in conversation.items()
        if key not in {"agent_decisions"}
    } | {
        "messages": [
            {key: value for key, value in message.items() if key != "decision"}
            for message in conversation["messages"]
        ]
    }


# ── Health & Diagnostics ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SpotifyCares Agent API",
        "database": "sqlite3",
    }


# ── Users Endpoints ──────────────────────────────────────────────────

@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(req: UserCreate):
    # Customer entry remains name/email based, but the server—not a client-supplied
    # user ID—creates the identity and grants an opaque session token.
    user = db.create_user(name=req.name.strip(), email=req.email.strip(), role="customer")
    return {**user, "access_token": db.create_session(user["id"])}


@app.get("/users/{user_id}")
def get_user(user_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User access denied")
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user


@app.get("/users/{user_id}/conversations")
def get_user_conversations(user_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """List the current user's conversations for the customer portal."""
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User access denied")
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return db.list_user_conversations(user_id)


# ── Admin Support Endpoints ──────────────────────────────────────────

@app.post("/admin/login")
def admin_login(req: AdminLoginRequest):
    """Authenticate the configured local-demo admin and issue a bearer session."""
    configured_email = os.getenv("SPOTIFY_AGENT_ADMIN_EMAIL", "").strip()
    configured_password = os.getenv("SPOTIFY_AGENT_ADMIN_PASSWORD", "")
    if not configured_email or not configured_password or not hmac.compare_digest(req.email.strip().lower(), configured_email.lower()) or not hmac.compare_digest(req.password, configured_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    user = db.create_user(name="Support Admin", email=configured_email, role="admin", user_id="admin_local_demo")
    return {**user, "access_token": db.create_session(user["id"])}


@app.get("/admin/conversations")
def list_admin_conversations(_: Dict[str, Any] = Depends(require_admin)):
    return db.list_admin_conversations()


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(authorization: Optional[str] = Header(None)):
    db.revoke_session(_bearer_token(authorization))


# ── Conversations Endpoints ──────────────────────────────────────────

@app.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(req: ConversationCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    if current_user["role"] != "customer" or req.user_id != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customers may only create their own conversations")
    if req.status != "open":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customers may only create open conversations")
    try:
        return db.create_conversation(user_id=req.user_id, status="open", conversation_id=req.id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation ID already exists")


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    conv = _require_conversation_owner(conversation_id, current_user)
    return conv if current_user["role"] == "admin" else _customer_conversation_view(conv)


@app.post("/conversations/{conversation_id}/admin-messages", status_code=status.HTTP_201_CREATED)
def send_admin_message(conversation_id: str, req: AdminMessageCreate, _: Dict[str, Any] = Depends(require_admin)):
    """Persist a human reply without invoking the AI pipeline."""
    conv = db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content cannot be empty")
    return db.add_message(conversation_id=conversation_id, sender="admin", content=content)


@app.patch("/conversations/{conversation_id}/status")
def update_conversation_status(conversation_id: str, req: ConversationStatusUpdate, _: Dict[str, Any] = Depends(require_admin)):
    conversation = db.update_conversation_status(conversation_id, req.status)
    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return conversation


# ── Messages & Agent Execution ───────────────────────────────────────

@app.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: str, req: MessageCreate, current_user: Dict[str, Any] = Depends(get_current_user)):
    msg_text = (req.content or req.message or req.text or "").strip()
    if not msg_text:
        raise HTTPException(status_code=422, detail="Message content cannot be empty")

    if req.sender != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customers may only send customer messages")
    if current_user["role"] != "customer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required")
    _require_conversation_owner(conversation_id, current_user)

    # 1. Save customer message
    cust_msg = db.add_message(
        conversation_id=conversation_id,
        sender="customer",
        content=msg_text,
    )

    # 2. Call existing SpotifyAgent pipeline
    agent_result = agent_run(msg_text)

    if isinstance(agent_result, dict):
        intent = agent_result.get("intent", "playback_error")
        confidence = float(agent_result.get("intent_confidence", 0.0))
        platform = agent_result.get("platform", "unknown")
        draft_reply = agent_result.get("draft_reply", "")
        decision = agent_result.get("decision", "AUTO_HANDLE")
        reason = agent_result.get("escalation_reason", "")
        evidence = agent_result.get("retrieved_evidence", [])
        risk_signals = agent_result.get("risk_signals", [])
        gen_mode = agent_result.get("generation_mode", "")
    else:
        intent = getattr(agent_result, "intent", "playback_error")
        confidence = float(getattr(agent_result, "intent_confidence", 0.0))
        platform = getattr(agent_result, "platform", "unknown")
        draft_reply = getattr(agent_result, "draft_reply", "")
        decision = getattr(agent_result, "decision", "AUTO_HANDLE")
        reason = getattr(agent_result, "escalation_reason", "")
        evidence = getattr(agent_result, "retrieved_evidence", []) or []
        risk_signals = getattr(agent_result, "risk_signals", []) or []
        gen_mode = getattr(agent_result, "generation_mode", "")

    # 3. Save agent response as a message
    agent_msg = db.add_message(
        conversation_id=conversation_id,
        sender="agent",
        content=draft_reply,
    )

    # 4. Save agent decision in agent_decisions
    decision_record = db.add_agent_decision(
        message_id=cust_msg["id"],
        intent=intent,
        confidence=confidence,
        platform=platform,
        decision=decision,
        escalation_reason=reason,
        response=draft_reply,
        retrieval_evidence=evidence,
    )

    # Escalation is a workflow state for the support inbox. The decision record
    # remains intact so an admin can review why the agent requested a takeover.
    if decision == "ESCALATE":
        db.update_conversation_status(conversation_id, "escalated")

    # 5. Return complete agent result
    response = {
        "conversation_id": conversation_id,
        "customer_message_id": cust_msg["id"],
        "agent_message_id": agent_msg["id"],
        "message_id": cust_msg["id"],
        "message": msg_text,
        "intent": intent,
        "confidence": confidence,
        "intent_confidence": confidence,
        "platform": platform,
        "decision": decision,
        "escalation_reason": reason,
        "reason": reason,
        "response": draft_reply,
        "draft_reply": draft_reply,
        "generation_mode": gen_mode,
        "risk_signals": risk_signals,
        "retrieved_evidence": evidence,
        "agent_decision_id": decision_record["id"],
    }
    # Customer clients only need the generated response. Decision rationale and
    # retrieval evidence remain visible to an authenticated admin via detail.
    return {key: response[key] for key in ("conversation_id", "customer_message_id", "agent_message_id", "response", "draft_reply")}


# ── Backward-compatible /predict endpoint ────────────────────────────

@app.post("/predict")
def predict(req: PredictRequest, _: Dict[str, Any] = Depends(require_admin)):
    result = agent_run(req.message)
    evidence = [
        {
            "customer_msg":   e.get("customer_msg", ""),
            "brand_response": e.get("brand_response", ""),
            "platform":       e.get("platform", ""),
            "score":          e.get("score", 0),
            "platform_match": e.get("platform_match", False),
        }
        for e in (result.get("retrieved_evidence") or [])
    ] if isinstance(result, dict) else [
        {
            "customer_msg":   e["customer_msg"],
            "brand_response": e["brand_response"],
            "platform":       e["platform"],
            "score":          e["score"],
            "platform_match": e.get("platform_match", False),
        }
        for e in (result.retrieved_evidence or [])
    ]

    if isinstance(result, dict):
        return {
            "intent":             result["intent"],
            "confidence":         result["intent_confidence"],
            "platform":           result["platform"],
            "response":           result["draft_reply"],
            "decision":           result["decision"],
            "reason":             result["escalation_reason"],
            "retrieved_evidence": evidence,
        }
    return {
        "intent":             result.intent,
        "confidence":         result.intent_confidence,
        "platform":           result.platform,
        "response":           result.draft_reply,
        "decision":           result.decision,
        "reason":             result.escalation_reason,
        "retrieved_evidence": evidence,
    }
