"""
Response generator.

Uses OpenAI (gpt-4o-mini by default) to produce a grounded reply
from retrieved evidence + the customer message.

Falls back to a template-based generator if no API key is set.
"""

import os, sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, OPENAI_API_KEY
from retriever import Evidence

SYSTEM_PROMPT = """You are a SpotifyCares support agent replying to a customer tweet.

Rules:
1. Base your reply ONLY on the provided historical evidence.
2. Do NOT invent Spotify policies or features not mentioned in evidence.
3. Do NOT fabricate URLs, version numbers, or specific settings paths.
4. If evidence is insufficient, say so honestly and suggest the customer contacts Spotify support directly via DM.
5. Keep the reply concise (2–4 sentences), empathetic, and actionable.
6. Match the informal but helpful tone of real Spotify support tweets.
7. Do NOT repeat the customer's name or @handle.
8. If the issue sounds like an account security or billing dispute, recommend human support.
"""

def _format_evidence(evidence: list[Evidence]) -> str:
    if not evidence:
        return "No historical evidence available."
    lines = []
    for i, e in enumerate(evidence, 1):
        lines.append(f"[Evidence {i}] (similarity={e.similarity:.2f}, "
                     f"platform={e.platform}, type={e.response_type})")
        lines.append(f"  Customer asked: {e.customer_msg[:150]}")
        lines.append(f"  Agent replied:  {e.brand_response[:250]}")
    return "\n".join(lines)


def generate_with_llm(
    customer_msg: str,
    evidence: list[Evidence],
    intent: str,
    platform: str,
) -> tuple[str, bool]:
    """
    Returns (draft_response, used_llm).
    used_llm=False means template fallback was used.
    """
    if not OPENAI_API_KEY:
        return _template_fallback(customer_msg, evidence, intent, platform), False

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        user_content = f"""Customer message: "{customer_msg}"

Intent detected: {intent}
Platform detected: {platform}

Historical evidence from similar resolved cases:
{_format_evidence(evidence)}

Write a brief, helpful reply to this customer."""

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_content},
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        return response.choices[0].message.content.strip(), True
    except Exception as e:
        print(f"  [generator] LLM error: {e} — using fallback", flush=True)
        return _template_fallback(customer_msg, evidence, intent, platform), False


def _template_fallback(
    customer_msg: str,
    evidence: list[Evidence],
    intent: str,
    platform: str,
) -> str:
    """
    Rule-based template fallback when no LLM API is available.
    Uses the top retrieved response directly, lightly adapted.
    """
    if not evidence:
        return ("Hi! We're sorry you're having trouble. "
                "Please DM us with more details so we can help. /SC")

    top = evidence[0]
    resp = top.brand_response

    # If the best evidence response is a DM redirect, compose a better reply
    if "dm" in resp.lower() and len(resp) < 100:
        intent_hints = {
            "playback_error":      "try restarting the app and clearing the cache",
            "account_login":       "try resetting your password at spotify.com/password",
            "premium_subscription":"check your subscription status in Account settings",
            "billing_charge":      "review your payment history in Account > Subscription",
            "app_crash_bug":       "try reinstalling the app and checking for updates",
            "playlist_library":    "try logging out and back in to resync your library",
            "content_unavailable": "some content may not be available in your region",
            "device_platform":     "try disconnecting and reconnecting the device in Spotify settings",
            "offline_download":    "try toggling offline mode off and on and re-downloading",
        }
        hint = intent_hints.get(intent, "please try restarting the app")
        return (f"Hi! Sorry you're having trouble. "
                f"You can {hint}. If that doesn't help, please DM us! /SC")

    return resp
