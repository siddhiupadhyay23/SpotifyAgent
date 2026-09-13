"""
FastAPI backend for SpotifyCares AI Support Agent.
Supports interactive customer conversations with SQLite persistence.

Run: uvicorn api:app --reload --port 8000
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from contextlib import asynccontextmanager

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, status
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
)

# Enable CORS for local demo and frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ────────────────────────────────────────

class PredictRequest(BaseModel):
    message: str


class UserCreate(BaseModel):
    name: str = Field(..., description="User full name or display name")
    email: str = Field(..., description="User email address")
    role: str = Field("customer", description="Role: 'customer' or 'agent'")
    id: Optional[str] = Field(None, description="Optional custom user ID")


class ConversationCreate(BaseModel):
    user_id: str = Field(..., description="User ID associated with conversation")
    status: str = Field("open", description="Conversation status (e.g. 'open', 'closed')")
    id: Optional[str] = Field(None, description="Optional custom conversation ID")


class MessageCreate(BaseModel):
    content: Optional[str] = Field(None, description="Message text")
    message: Optional[str] = Field(None, description="Alternative field for message text")
    text: Optional[str] = Field(None, description="Alternative field for message text")
    sender: str = Field("customer", description="Sender: 'customer' or 'agent'")


class AdminLoginRequest(BaseModel):
    name: str = Field("Support Admin", description="Display name for the local demo admin")
    email: str = Field("admin@spotifyagent.local", description="Email for the local demo admin")
    id: str = Field("admin_demo", description="Stable local demo admin ID")


class AdminMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Human admin reply text")


class ConversationStatusUpdate(BaseModel):
    status: Literal["open", "escalated", "resolved"]


# ── Health & Diagnostics ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SpotifyCares Agent API",
        "database": "sqlite3",
        "db_path": str(db.DB_PATH),
    }


# ── Users Endpoints ──────────────────────────────────────────────────

@app.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(req: UserCreate):
    return db.create_user(name=req.name, email=req.email, role=req.role, user_id=req.id)


@app.get("/users/{user_id}")
def get_user(user_id: str):
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user


@app.get("/users/{user_id}/conversations")
def get_user_conversations(user_id: str):
    """List the current user's conversations for the customer portal."""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return db.list_user_conversations(user_id)


# ── Admin Support Endpoints ──────────────────────────────────────────

@app.post("/admin/login")
def admin_login(req: AdminLoginRequest):
    """Create or return the local demo admin account.

    This is intentionally a lightweight role-based demo entry point, not
    production authentication.
    """
    return db.create_user(name=req.name, email=req.email, role="admin", user_id=req.id)


@app.get("/admin/conversations")
def list_admin_conversations():
    return db.list_admin_conversations()


# ── Conversations Endpoints ──────────────────────────────────────────

@app.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(req: ConversationCreate):
    return db.create_conversation(user_id=req.user_id, status=req.status, conversation_id=req.id)


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    conv = db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return conv


@app.post("/conversations/{conversation_id}/admin-messages", status_code=status.HTTP_201_CREATED)
def send_admin_message(conversation_id: str, req: AdminMessageCreate):
    """Persist a human reply without invoking the AI pipeline."""
    conv = db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content cannot be empty")
    return db.add_message(conversation_id=conversation_id, sender="admin", content=content)


@app.patch("/conversations/{conversation_id}/status")
def update_conversation_status(conversation_id: str, req: ConversationStatusUpdate):
    conversation = db.update_conversation_status(conversation_id, req.status)
    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return conversation


# ── Messages & Agent Execution ───────────────────────────────────────

@app.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: str, req: MessageCreate):
    msg_text = (req.content or req.message or req.text or "").strip()
    if not msg_text:
        raise HTTPException(status_code=422, detail="Message content cannot be empty")

    conv = db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")

    # 1. Save customer message
    cust_msg = db.add_message(
        conversation_id=conversation_id,
        sender=req.sender,
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
    return {
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


# ── Backward-compatible /predict endpoint ────────────────────────────

@app.post("/predict")
def predict(req: PredictRequest):
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
