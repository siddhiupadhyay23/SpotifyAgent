"""
Minimal FastAPI wrapper around the existing SpotifyCares agent.
Run: uvicorn api:app --reload --port 8000
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from pydantic import BaseModel
from agent import run as agent_run

app = FastAPI(title="SpotifyCares Agent API")


class PredictRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


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
            "intent":     result["intent"],
            "confidence": result["intent_confidence"],
            "platform":   result["platform"],
            "response":   result["draft_reply"],
            "decision":   result["decision"],
            "reason":     result["escalation_reason"],
            "retrieved_evidence": evidence,
        }
    return {
        "intent":     result.intent,
        "confidence": result.intent_confidence,
        "platform":   result.platform,
        "response":   result.draft_reply,
        "decision":   result.decision,
        "reason":     result.escalation_reason,
        "retrieved_evidence": evidence,
    }
