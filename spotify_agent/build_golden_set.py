"""
STEP 3 — Build the golden evaluation set.

Samples 200 examples from the held-out test pool (conversations after
the temporal split cutoff), stratified by intent.

Each example is AUTO-LABELLED using the embedding classifier, then
written to golden_set.jsonl for manual review / refinement.

The golden set is the ONLY source of ground-truth for all evaluations.
It is kept strictly separate from the retrieval corpus.

Run: python build_golden_set.py
"""

import json, sys, random
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    PROC_DIR, GOLDEN_DIR, GOLDEN_FILE, GOLDEN_CSV,
    GOLDEN_PER_INTENT, INTENTS, INTENT_LABELS,
    extract_platform, ESCALATION_KEYWORDS, RANDOM_SEED,
    HIGH_RISK_INTENTS,
)

GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
random.seed(RANDOM_SEED)

# ── Load test pool ────────────────────────────────────────────────────────────
test_path = PROC_DIR / "test_pool_conversations.jsonl"
print(f"Loading test pool from {test_path} ...", flush=True)
test_convos = []
with open(test_path, encoding="utf-8") as f:
    for line in f:
        test_convos.append(json.loads(line))
print(f"  {len(test_convos):,} conversations in test pool")

# ── Extract candidate examples ────────────────────────────────────────────────
# A candidate = first customer message in a conversation that has a
# SpotifyCares response, and whose response is not DM-only.
from config import BRAND, DM_ONLY_PATTERN
import re

TROUBLE_PAT = re.compile(
    r'\b(try|restart|reset|clear.?cache|reinstall|update|check|'
    r'verify|enable|disable|log.?out|sign.?out|steps|follow)\b', re.I)

candidates = []
for convo in test_convos:
    turns = convo["turns"]
    # find first customer→brand pair
    for i in range(len(turns) - 1):
        if turns[i]["inbound"] and turns[i+1]["author"] == BRAND:
            cust_msg  = turns[i]["text"].strip()
            brand_resp = turns[i+1]["text"].strip()
            if not cust_msg or not brand_resp:
                continue
            if len(cust_msg) < 15:
                continue
            # skip if brand response is pure DM redirect with no content
            if DM_ONLY_PATTERN.match(brand_resp) and len(brand_resp) < 100:
                continue
            has_resolution = bool(TROUBLE_PAT.search(brand_resp))
            has_escalation = bool(ESCALATION_KEYWORDS.search(cust_msg))
            platform = extract_platform(cust_msg)
            candidates.append({
                "customer_msg":    cust_msg,
                "brand_response":  brand_resp,
                "platform":        platform,
                "convo_id":        convo["root_id"],
                "conv_length":     convo["length"],
                "has_resolution":  has_resolution,
                "has_escalation_signal": has_escalation,
                "ts":              turns[i]["ts"],
            })
            break   # one example per conversation

print(f"  {len(candidates):,} candidate examples extracted from test pool")

# ── Classify intent for all candidates ───────────────────────────────────────
from intent_classifier import get_classifier
clf = get_classifier()
print("Classifying candidates ...", flush=True)

texts = [c["customer_msg"] for c in candidates]
preds = clf.classify_batch(texts)
for c, p in zip(candidates, preds):
    c["intent"]      = p["intent"]
    c["confidence"]  = p["confidence"]
    c["auto_label"]  = True   # flagged for human review

# ── Stratified sampling ───────────────────────────────────────────────────────
by_intent = defaultdict(list)
for c in candidates:
    by_intent[c["intent"]].append(c)

golden = []
for intent, target_n in GOLDEN_PER_INTENT.items():
    pool = by_intent.get(intent, [])
    if not pool:
        print(f"  WARNING: no candidates for intent '{intent}'")
        continue

    # Sort: prefer higher confidence + variety of platforms
    # Include some hard examples: low confidence, escalation signals, multi-platform
    pool.sort(key=lambda x: -x["confidence"])

    easy  = [x for x in pool if x["confidence"] >= 0.55 and not x["has_escalation_signal"]]
    hard  = [x for x in pool if x["confidence"] < 0.55 or x["has_escalation_signal"]]
    esc   = [x for x in pool if x["has_escalation_signal"]]

    # Compose: 60% easy, 25% hard, 15% escalation-signal (with overlap OK)
    n_easy = int(target_n * 0.60)
    n_hard = int(target_n * 0.25)
    n_esc  = target_n - n_easy - n_hard

    sampled_ids = set()
    selected = []

    def add_from(src, n):
        added = 0
        for item in src:
            cid = item["convo_id"]
            if cid not in sampled_ids and added < n:
                sampled_ids.add(cid)
                selected.append(item)
                added += 1

    add_from(easy[:], n_easy)
    add_from(hard[:], n_hard)
    add_from(esc[:],  n_esc)

    # Top-up if needed
    remaining = target_n - len(selected)
    if remaining > 0:
        extras = [x for x in pool if x["convo_id"] not in sampled_ids]
        add_from(extras, remaining)

    print(f"  {intent:<25} target={target_n:>3}  sampled={len(selected):>3}  "
          f"(pool={len(pool):>4}, hard={len(hard):>3}, esc={len(esc):>3})")
    for s in selected:
        s["intent"] = intent   # enforce correct intent label
    golden.extend(selected)

random.shuffle(golden)
# Assign final IDs
for i, g in enumerate(golden):
    g["golden_id"] = f"g{i+1:04d}"

print(f"\nTotal golden examples: {len(golden)}")

# Escalation labels: escalate if high-risk intent + escalation keyword
for g in golden:
    should_escalate = (
        g["has_escalation_signal"] or
        (g["intent"] in HIGH_RISK_INTENTS and g["confidence"] < 0.50)
    )
    g["escalation_label"] = "ESCALATE" if should_escalate else "AUTO_HANDLE"

esc_count = sum(1 for g in golden if g["escalation_label"] == "ESCALATE")
print(f"Escalation labels  : {esc_count} ESCALATE, {len(golden)-esc_count} AUTO_HANDLE")

# Platform distribution
from collections import Counter
plat_dist = Counter(g["platform"] for g in golden)
print("Platform distribution:")
for p, n in sorted(plat_dist.items(), key=lambda x: -x[1]):
    print(f"  {p:<15} {n:>3}")

# ── Save ──────────────────────────────────────────────────────────────────────
with open(GOLDEN_FILE, "w", encoding="utf-8") as f:
    for g in golden:
        f.write(json.dumps(g, ensure_ascii=False) + "\n")
print(f"\nSaved golden set → {GOLDEN_FILE}")

# Also save as CSV for easy inspection
import pandas as pd
gdf = pd.DataFrame([{
    "golden_id":       g["golden_id"],
    "customer_msg":    g["customer_msg"],
    "intent":          g["intent"],
    "confidence":      g["confidence"],
    "platform":        g["platform"],
    "escalation_label":g["escalation_label"],
    "has_escalation_signal": g["has_escalation_signal"],
    "has_resolution":  g["has_resolution"],
    "brand_response":  g["brand_response"],
    "convo_id":        g["convo_id"],
    "ts":              g["ts"],
} for g in golden])
gdf.to_csv(GOLDEN_CSV, index=False)
print(f"Saved golden CSV  → {GOLDEN_CSV}")
print("\nbuild_golden_set complete.")
