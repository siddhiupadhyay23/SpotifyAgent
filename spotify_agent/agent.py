"""
SpotifyCares Support Agent — final pipeline.

Pipeline:
  customer message
  -> intent classification  (TF-IDF + LR)
  -> platform extraction    (regex)
  -> risk detection         (rules)
  -> hybrid retrieval       (TF-IDF cosine + Jaccard + platform boost)
  -> response generation    (LLM if key set, else template fallback)
  -> escalation decision    (rules + configurable thresholds)
  -> structured JSON result
"""

import json, os, re, pickle, sys
from pathlib import Path

ROOT   = Path(__file__).parent
MODELS = ROOT / "models"
sys.path.insert(0, str(ROOT))

from retrieval.hybrid_retriever import retrieve_hybrid

# ── configurable thresholds (tune on val later) ───────────────────
CONF_ESCALATE_HARD   = 0.40   # always escalate below this
CONF_ESCALATE_RISKY  = 0.65   # escalate if also high-risk intent
MIN_EVIDENCE_SCORE   = 0.12   # escalate if best retrieval < this
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# ── load classifier once ──────────────────────────────────────────
_vec = _clf = None
def _load_clf():
    global _vec, _clf
    if _vec is None:
        with open(MODELS / "tfidf_vec.pkl", "rb") as f: _vec = pickle.load(f)
        with open(MODELS / "lr_clf.pkl",    "rb") as f: _clf = pickle.load(f)

def classify_intent(msg: str) -> dict:
    _load_clf()
    X    = _vec.transform([msg])
    lbl  = _clf.predict(X)[0]
    prob = float(_clf.predict_proba(X).max())
    return {"intent": lbl, "confidence": round(prob, 4)}

# ── platform extraction ───────────────────────────────────────────
_PLAT_PATTERNS = [
    ("android",  re.compile(r"\b(android|samsung|galaxy|pixel|oneplus)\b", re.I)),
    ("ios",      re.compile(r"\b(ios|iphone|ipad|apple)\b", re.I)),
    ("windows",  re.compile(r"\b(windows|pc\b|desktop|laptop)\b", re.I)),
    ("mac",      re.compile(r"\b(mac\b|macos|macbook|imac)\b", re.I)),
    ("alexa",    re.compile(r"\b(alexa|echo\b)\b", re.I)),
    ("sonos",    re.compile(r"\b(sonos)\b", re.I)),
    ("tv",       re.compile(r"\b(tv\b|smart.?tv|chromecast|firetv|fire.?stick|roku|apple.?tv)\b", re.I)),
    ("car",      re.compile(r"\b(car\b|carplay|android.?auto|vehicle)\b", re.I)),
    ("ps",       re.compile(r"\b(ps[34]\b|playstation)\b", re.I)),
    ("web",      re.compile(r"\b(browser|chrome\b|firefox|safari|web.?player)\b", re.I)),
]

def extract_platform(msg: str) -> str:
    for name, pat in _PLAT_PATTERNS:
        if pat.search(msg):
            return name
    return "unknown"

# ── risk detection ────────────────────────────────────────────────
_RISK_RULES = [
    ("billing_dispute",
     re.compile(r"\b(unauthorized.?charg|chargeback|charge.?back|dispute|"
                r"wrong.?charg|overcharg|charged.?twice|duplicate.?charg|"
                r"refund.?or|money.?back.+immediately)\b", re.I)),
    ("account_compromise",
     re.compile(r"\b(hack|hacked|compromis|unauthori[sz]|stolen|someone.?else|"
                r"account.?stolen|not.?me|i.?didnt.?do)\b", re.I)),
    ("legal_threat",
     re.compile(r"\b(lawyer|legal.?action|sue\b|suing|court\b|fraud\b|"
                r"trading.?standards|consumer.?rights)\b", re.I)),
    ("explicit_urgency",
     re.compile(r"\b(urgent|emergency|asap|right.?now|immediately|"
                r"call.?me.?now|please.?help.?now)\b", re.I)),
]

HIGH_RISK_INTENTS = {"billing_charge", "account_login"}

def detect_risk(msg: str, intent: str) -> list[str]:
    signals = []
    for name, pat in _RISK_RULES:
        if pat.search(msg):
            signals.append(name)
    if intent in HIGH_RISK_INTENTS:
        signals.append(f"high_risk_intent:{intent}")
    return signals

# ── response generation ───────────────────────────────────────────
_SYS_PROMPT = (
    "You are a SpotifyCares support agent replying to a customer on Twitter. "
    "Rules: "
    "1. Base your reply ONLY on the provided historical evidence. "
    "2. Do NOT invent Spotify policies, prices, refund procedures, or troubleshooting "
    "steps that are not present in the evidence. "
    "3. If evidence is insufficient, say so and ask the customer to DM. "
    "4. Keep reply under 3 sentences. Be empathetic and direct. "
    "5. Do not repeat the customer's @handle."
)

_FALLBACK = {
    "playback_error":       "Hi! Try restarting Spotify and checking your connection. If it keeps happening, reinstall the app. /SC",
    "account_login":        "Hi! Try resetting your password at spotify.com/password-reset. Clear app data and retry. /SC",
    "premium_subscription": "Hi! Check your subscription status at spotify.com/account. /SC",
    "billing_charge":       "Hi! Review your billing history at spotify.com/account. For charge disputes please DM us. /SC",
    "app_crash_bug":        "Hi! Force-close Spotify and reopen it. If it keeps crashing, try reinstalling. /SC",
    "playlist_library":     "Hi! Try logging out and back in to resync your library. /SC",
    "content_unavailable":  "Hi! Some content isn't available in all regions due to licensing. /SC",
    "device_platform":      "Hi! Try disconnecting and reconnecting the device in Spotify Settings > Devices. /SC",
    "offline_download":     "Hi! Toggle offline mode off then on, and re-download your tracks. /SC",
}

_DM_PAT   = re.compile(r"\b(dm|direct.?message)\b", re.I)
_USEFUL   = re.compile(
    r"\b(try|restart|reset|clear.?cache|reinstall|update|check|verify|"
    r"enable|disable|log.?out|sign.?out|toggle|go.?to|navigate)\b", re.I)

def generate_response(msg: str, intent: str, evidence: list) -> tuple[str, str]:
    """Returns (draft_reply, generation_mode)."""
    if OPENAI_KEY:
        ev_text = ""
        for i, e in enumerate(evidence, 1):
            ev_text += (f"\n[{i}] sim={e['score']:.3f}  platform={e['platform']}\n"
                        f"  Customer: {e['customer_msg'][:150]}\n"
                        f"  Agent:    {e['brand_response'][:200]}\n")
        user_msg = (f'Customer message: "{msg}"\nIntent: {intent}\n'
                    f'Historical evidence:{ev_text}\nWrite a helpful reply.')
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_KEY)
            r = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role":"system","content":_SYS_PROMPT},
                          {"role":"user",  "content":user_msg}],
                temperature=0.3, max_tokens=200,
            )
            return r.choices[0].message.content.strip(), f"llm:{LLM_MODEL}"
        except Exception as e:
            return f"[LLM error: {e}]", "llm_error"

    # Template fallback: prefer useful historical response over generic template
    for ev in evidence:
        resp = ev.get("brand_response","")
        if _USEFUL.search(resp) and not (_DM_PAT.search(resp) and len(resp) < 100):
            clean = re.sub(r"@\S+\s*", "", resp).strip()
            if len(clean) > 30:
                return clean, "template_fallback:top_evidence"

    return _FALLBACK.get(intent,
        "Hi! Sorry for the trouble — please DM us with details. /SC"), "template_fallback:intent"

# ── escalation decision ───────────────────────────────────────────
def decide_escalation(intent: str, confidence: float,
                      risk_signals: list, evidence: list,
                      conf_hard: float = CONF_ESCALATE_HARD,
                      conf_risky: float = CONF_ESCALATE_RISKY,
                      min_evidence: float = MIN_EVIDENCE_SCORE) -> dict:
    reasons = []
    best_score = evidence[0]["score"] if evidence else 0.0

    # Rule 1: hard security / legal signals
    hard_signals = {"billing_dispute","account_compromise","legal_threat"}
    hit = hard_signals & set(risk_signals)
    if hit:
        reasons.append(f"High-risk signal(s) detected: {', '.join(hit)}")

    # Rule 2: confidence too low
    if confidence < conf_hard:
        reasons.append(f"Intent confidence {confidence:.2f} below hard threshold {conf_hard}")
    elif confidence < conf_risky and any("high_risk_intent" in s for s in risk_signals):
        reasons.append(f"High-risk intent with marginal confidence {confidence:.2f}")

    # Rule 3: insufficient retrieval evidence
    if best_score < min_evidence:
        reasons.append(f"Best retrieval score {best_score:.3f} below minimum {min_evidence}")

    decision = "ESCALATE" if reasons else "AUTO_HANDLE"
    return {
        "decision": decision,
        "escalation_reason": "; ".join(reasons) if reasons else "Intent clear, evidence sufficient, no risk signals",
    }

# ── main pipeline ─────────────────────────────────────────────────
def run(message: str,
        conf_hard:  float = CONF_ESCALATE_HARD,
        conf_risky: float = CONF_ESCALATE_RISKY,
        min_ev:     float = MIN_EVIDENCE_SCORE) -> dict:

    # 1. Intent
    clf_out    = classify_intent(message)
    intent     = clf_out["intent"]
    confidence = clf_out["confidence"]

    # 2. Platform
    platform = extract_platform(message)

    # 3. Risk
    risk_signals = detect_risk(message, intent)

    # 4. Retrieval
    evidence = retrieve_hybrid(message, top_k=3)
    evidence_out = [
        {"customer_msg":   e["customer_msg"][:200],
         "brand_response": e["brand_response"][:300],
         "platform":       e["platform"],
         "score":          e["score"],
         "platform_match": e.get("platform_match", False)}
        for e in evidence
    ]

    # 5. Escalation (before generation — skip LLM on hard escalations)
    esc = decide_escalation(intent, confidence, risk_signals, evidence,
                            conf_hard, conf_risky, min_ev)

    # 6. Generation
    if esc["decision"] == "ESCALATE" and any(
            s in risk_signals for s in ("billing_dispute","account_compromise","legal_threat")):
        draft = ("We understand this is urgent. Please DM us with your account "
                 "details and a specialist will assist you right away. /SC")
        gen_mode = "escalation_override"
    else:
        draft, gen_mode = generate_response(message, intent, evidence)

    return {
        "message":            message,
        "intent":             intent,
        "intent_confidence":  confidence,
        "platform":           platform,
        "risk_signals":       risk_signals,
        "retrieved_evidence": evidence_out,
        "draft_reply":        draft,
        "generation_mode":    gen_mode,
        "decision":           esc["decision"],
        "escalation_reason":  esc["escalation_reason"],
    }


# ── smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    TEST_MESSAGES = [
        ("playback + Android",  "Spotify keeps stopping every 30 seconds on my Android phone"),
        ("billing/charge",      "I was charged twice for premium this month, this is unacceptable"),
        ("login/account",       "Can't log into my account, says invalid password but I just reset it"),
        ("playlist/library",    "My entire liked songs playlist just disappeared after the update"),
        ("unclear/low-conf",    "nothing works please just help me"),
    ]

    for label, msg in TEST_MESSAGES:
        print(f"\n{'='*60}")
        print(f"TEST: {label}")
        print(f"{'='*60}")
        result = run(msg)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\nDONE. Stopping.")
