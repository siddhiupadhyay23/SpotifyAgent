"""
Simple RAG baseline.

Pipeline:
  customer message
  -> TF-IDF intent classification (existing model)
  -> retrieve top-3 historical examples (existing retriever.py)
  -> generate response (LLM if key set, else rule-based template)
  -> save predictions

No platform filtering. No risk-aware escalation. Intentionally simple.

Run: python baselines/simple_rag.py
  or: OPENAI_API_KEY=sk-... python baselines/simple_rag.py
"""

import json, pickle, sys, os, time, re
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
GOLDEN  = ROOT / "golden_set"  / "golden_set.jsonl"
MODELS  = ROOT / "models"
RESULTS = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))
from retriever import retrieve_similar   # 500-example Jaccard retriever

# ── load trained classifier ───────────────────────────────────────
print("Loading classifier ...", flush=True)
with open(MODELS / "tfidf_vec.pkl", "rb") as f:
    vec = pickle.load(f)
with open(MODELS / "lr_clf.pkl", "rb") as f:
    clf = pickle.load(f)

def classify(msg: str) -> tuple[str, float]:
    X   = vec.transform([msg])
    lbl = clf.predict(X)[0]
    prob = clf.predict_proba(X).max()
    return lbl, round(float(prob), 4)

# ── LLM generation ────────────────────────────────────────────────
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
USE_LLM    = bool(OPENAI_KEY)

SYSTEM_PROMPT = (
    "You are a SpotifyCares support agent replying to a customer tweet. "
    "Rules: "
    "1. Answer ONLY from the provided historical evidence. "
    "2. Do NOT invent Spotify policies, URLs, or troubleshooting steps absent from evidence. "
    "3. If evidence is insufficient, say so and recommend the customer DM SpotifyCares. "
    "4. Keep replies brief (2-3 sentences), empathetic, and actionable. "
    "5. Match the tone of real SpotifyCares tweets."
)

def build_user_prompt(msg: str, intent: str, evidence: list) -> str:
    ev_text = ""
    for i, e in enumerate(evidence, 1):
        ev_text += (
            f"\n[Evidence {i}] similarity={e['score']:.3f}\n"
            f"  Customer: {e['customer_msg'][:150]}\n"
            f"  Agent:    {e['brand_response'][:200]}\n"
        )
    return (
        f'Customer message: "{msg}"\n'
        f"Detected intent: {intent}\n"
        f"\nHistorical evidence:\n{ev_text}\n"
        f"Write a helpful reply based only on the evidence above."
    )

def generate_llm(msg: str, intent: str, evidence: list) -> tuple[str, bool]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_user_prompt(msg, intent, evidence)},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip(), True
    except Exception as e:
        return f"[LLM error: {e}]", False

# ── Rule-based template fallback (no API key) ─────────────────────
# Uses the top retrieved historical response, lightly adapted.
DM_PAT  = re.compile(r"\b(dm|direct.?message)\b", re.I)
USEFUL  = re.compile(
    r"\b(try|restart|reset|clear.?cache|reinstall|update|check|"
    r"verify|enable|disable|log.?out|sign.?out)\b", re.I)

FALLBACK_TEMPLATES = {
    "playback_error":       "Hi! Try restarting the Spotify app and checking your internet connection. If it keeps stopping, reinstall the app. /SC",
    "account_login":        "Hi! Try resetting your password at spotify.com/password-reset. Clear app data and try again. /SC",
    "premium_subscription": "Hi! You can check your subscription status at spotify.com/account. /SC",
    "billing_charge":       "Hi! Please review your billing history at spotify.com/account. For payment disputes, please DM us. /SC",
    "app_crash_bug":        "Hi! Try force-closing and reopening Spotify. If it continues, try reinstalling the app. /SC",
    "playlist_library":     "Hi! Try logging out and back in to resync your library. /SC",
    "content_unavailable":  "Hi! Some content may not be available in your region due to licensing restrictions. /SC",
    "device_platform":      "Hi! Try disconnecting and reconnecting the device in Spotify Settings > Connect to a device. /SC",
    "offline_download":     "Hi! Try toggling offline mode off and back on, then re-download your tracks. /SC",
}

def generate_template(msg: str, intent: str, evidence: list) -> tuple[str, bool]:
    # Prefer top evidence response if it is informative
    for ev in evidence:
        resp = ev.get("brand_response", "")
        if USEFUL.search(resp) and not (DM_PAT.search(resp) and len(resp) < 100):
            # Trim @mentions from historical response for cleanliness
            clean = re.sub(r"@\w+\s*", "", resp).strip()
            if len(clean) > 30:
                return clean, False
    # Fall back to intent template
    return FALLBACK_TEMPLATES.get(intent,
        "Hi! We are sorry for the trouble. Please DM us so we can help. /SC"), False

def generate(msg: str, intent: str, evidence: list) -> tuple[str, bool]:
    if USE_LLM:
        return generate_llm(msg, intent, evidence)
    return generate_template(msg, intent, evidence)

# ── Load golden set ───────────────────────────────────────────────
golden = []
with open(GOLDEN, encoding="utf-8") as f:
    for line in f:
        golden.append(json.loads(line))
print(f"Golden set: {len(golden)} examples  |  LLM: {'YES ('+LLM_MODEL+')' if USE_LLM else 'NO - template fallback'}")

# ── Run RAG pipeline ──────────────────────────────────────────────
predictions = []
t_start = time.time()

for i, g in enumerate(golden):
    msg = g["customer_msg"]

    # 1. Classify
    intent, conf = classify(msg)

    # 2. Retrieve (no platform filter in this baseline)
    evidence = retrieve_similar(msg, top_k=3, platform_filter="unknown")

    # 3. Generate
    draft, used_llm = generate(msg, intent, evidence)

    predictions.append({
        "golden_id":        g["golden_id"],
        "customer_msg":     msg,
        "true_intent":      g["intent"],
        "pred_intent":      intent,
        "intent_confidence":conf,
        "platform":         g.get("platform","unknown"),
        "evidence":         evidence,
        "draft_response":   draft,
        "used_llm":         used_llm,
        "true_escalation":  g["escalation_label"],
    })

    if (i+1) % 50 == 0:
        print(f"  {i+1}/{len(golden)} ...", flush=True)

elapsed = time.time() - t_start
print(f"Done. {len(predictions)} examples in {elapsed:.1f}s")

# ── Quick metrics ─────────────────────────────────────────────────
from sklearn.metrics import accuracy_score, f1_score

true_i = [p["true_intent"]  for p in predictions]
pred_i = [p["pred_intent"]  for p in predictions]

acc    = accuracy_score(true_i, pred_i)
mf1    = f1_score(true_i, pred_i, average="macro",    zero_division=0)
wf1    = f1_score(true_i, pred_i, average="weighted", zero_division=0)

# Retrieval coverage: fraction where top-1 score > 0.15
retrieval_cov = sum(1 for p in predictions
                    if p["evidence"] and p["evidence"][0]["score"] > 0.15) / len(predictions)
avg_top1 = sum(p["evidence"][0]["score"] for p in predictions
               if p["evidence"]) / max(sum(1 for p in predictions if p["evidence"]), 1)

print(f"\nIntent  Accuracy   : {acc:.4f}")
print(f"Intent  Macro F1   : {mf1:.4f}")
print(f"Intent  Weighted F1: {wf1:.4f}")
print(f"Retrieval coverage : {retrieval_cov:.4f}  (score > 0.15)")
print(f"Avg top-1 sim score: {avg_top1:.4f}")

# ── 3 example outputs ─────────────────────────────────────────────
print("\n--- 3 Sample RAG Outputs ---")
for p in predictions[:3]:
    print(f"\n[{p['golden_id']}] Customer: {p['customer_msg'][:100]}")
    print(f"  True intent: {p['true_intent']}  |  Pred intent: {p['pred_intent']}  ({p['intent_confidence']:.2f})")
    if p["evidence"]:
        e = p["evidence"][0]
        print(f"  Top evidence (score={e['score']:.3f}): {e['customer_msg'][:80]}")
        print(f"    -> {e['brand_response'][:100]}")
    print(f"  Draft: {p['draft_response'][:120]}")

# ── Save ──────────────────────────────────────────────────────────
result_summary = {
    "retrieval_method":    "Jaccard token-overlap, top-3, sample=500, no platform filter",
    "classifier":          "TF-IDF + LogisticRegression (from simple_classifier.py)",
    "generation":          LLM_MODEL if USE_LLM else "rule-based template (no API key)",
    "golden_size":         len(predictions),
    "runtime_seconds":     round(elapsed, 1),
    "intent_accuracy":     round(acc, 4),
    "intent_macro_f1":     round(mf1, 4),
    "intent_weighted_f1":  round(wf1, 4),
    "retrieval_coverage":  round(retrieval_cov, 4),
    "avg_top1_score":      round(avg_top1, 4),
    "llm_used":            USE_LLM,
    "note": ("" if USE_LLM else
             "LLM generation requires OPENAI_API_KEY env var. "
             "Set it and rerun to enable grounded LLM responses. "
             "Intent classification and retrieval are unaffected."),
}

with open(RESULTS / "simple_rag.json", "w", encoding="utf-8") as f:
    json.dump(result_summary, f, indent=2)

with open(RESULTS / "simple_rag_predictions.jsonl", "w", encoding="utf-8") as f:
    for p in predictions:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

md = f"""# Simple RAG Baseline

**Pipeline:** TF-IDF+LR intent classifier -> Jaccard retrieval (top-3, 500-sample) -> {'LLM ('+LLM_MODEL+')' if USE_LLM else 'template generation (no API key)'}

No platform filtering. No risk-aware escalation. Intentionally simple.

## Results (n={len(predictions)})

| Metric | Score |
|---|---|
| Intent Accuracy | {acc:.4f} |
| Intent Macro F1 | {mf1:.4f} |
| Intent Weighted F1 | {wf1:.4f} |
| Retrieval Coverage (score>0.15) | {retrieval_cov:.4f} |
| Avg Top-1 Similarity | {avg_top1:.4f} |
| Runtime | {elapsed:.1f}s |

## Generation

{'LLM-powered: ' + LLM_MODEL if USE_LLM else '**No LLM API key set.** Template fallback used. Set OPENAI_API_KEY and rerun for grounded LLM generation.'}

## Notes

- Retrieval uses Jaccard token overlap on a 500-example sample.
- No platform-aware filtering (that is the Final System improvement).
- Intent classification is identical to Simple Classifier baseline.
"""
with open(RESULTS / "simple_rag.md", "w", encoding="utf-8") as f:
    f.write(md)

print(f"\nSaved -> results/simple_rag.json")
print(f"Saved -> results/simple_rag_predictions.jsonl")
print(f"Saved -> results/simple_rag.md")
if not USE_LLM:
    print("\nNOTE: No OPENAI_API_KEY found.")
    print("  Generation used template fallback.")
    print("  To enable LLM generation: set OPENAI_API_KEY=sk-... and rerun.")
print("DONE. Stopping.")
