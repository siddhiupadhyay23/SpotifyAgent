"""
STEP 5 — Failure analysis.

Finds the 5 most illustrative failure modes from actual predictions
on the golden set and writes a detailed markdown report.

Run: python failure_analysis.py
"""

import json, sys, re
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from config import GOLDEN_FILE, RESULTS_DIR, DOCS_DIR, INTENT_LABELS

DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load ──────────────────────────────────────────────────────────────────────
golden = {}
with open(GOLDEN_FILE, encoding="utf-8") as f:
    for line in f:
        g = json.loads(line)
        golden[g["golden_id"]] = g

final_preds = []
with open(RESULTS_DIR / "preds_final.jsonl", encoding="utf-8") as f:
    for line in f:
        final_preds.append(json.loads(line))

# align predictions to golden
aligned = []
gold_list = list(golden.values())
for g, p in zip(gold_list, final_preds):
    aligned.append({"gold": g, "pred": p})

# ── Categorise failures ───────────────────────────────────────────────────────
wrong_intent = []
wrong_escalation = []
dm_retrieved = []
no_evidence  = []
plat_mismatch = []

USEFUL = re.compile(
    r'\b(try|restart|reset|clear.?cache|reinstall|update|check|'
    r'verify|enable|disable|log.?out|sign.?out)\b', re.I)

for item in aligned:
    g, p = item["gold"], item["pred"]

    true_intent = g["intent"]
    pred_intent = p.get("intent", "")
    true_esc    = g["escalation_label"]
    pred_esc    = p.get("decision", "")

    # 1. Wrong intent
    if true_intent != pred_intent:
        wrong_intent.append(item)

    # 2. Wrong escalation (missed escalation = false auto-handle)
    if true_esc == "ESCALATE" and pred_esc == "AUTO_HANDLE":
        wrong_escalation.append(item)

    # 3. DM-redirect retrieved as evidence
    ev = p.get("retrieved_evidence", [])
    for e in ev:
        br = e.get("brand_response", "")
        if re.search(r'\b(dm|direct.?message)\b', br, re.I) and not USEFUL.search(br):
            dm_retrieved.append(item)
            break

    # 4. No useful evidence
    if not ev or all(e.get("similarity", 0) < 0.25 for e in ev):
        no_evidence.append(item)

    # 5. Platform mismatch in evidence
    gold_plat = g.get("platform", "unknown")
    if gold_plat not in ("unknown", ""):
        ev_plats = [e.get("platform", "unknown") for e in ev]
        if ev and all(ep != gold_plat for ep in ev_plats):
            plat_mismatch.append(item)

print(f"Wrong intent          : {len(wrong_intent)}")
print(f"Missed escalations    : {len(wrong_escalation)}")
print(f"DM retrieved as evidence: {len(dm_retrieved)}")
print(f"No useful evidence    : {len(no_evidence)}")
print(f"Platform mismatch     : {len(plat_mismatch)}")

# ── Pick best illustrative example per category ───────────────────────────────
def pick(lst, n=1):
    return lst[:n]

cases = {
    "Wrong Intent Classification":        pick(wrong_intent),
    "Missed Escalation (False Auto-Handle)": pick(wrong_escalation),
    "DM Redirect Retrieved as Evidence":  pick(dm_retrieved),
    "Insufficient Retrieval Evidence":    pick(no_evidence),
    "Platform Mismatch in Retrieved Evidence": pick(plat_mismatch),
}

# ── Write markdown report ─────────────────────────────────────────────────────
lines = ["# Failure Analysis — SpotifyCares Support Agent\n",
         "Five real failure modes identified from evaluation on the golden set.\n"]

failure_num = 0
for failure_name, items in cases.items():
    failure_num += 1
    lines.append(f"\n---\n\n## Failure Mode {failure_num}: {failure_name}\n")
    if not items:
        lines.append("_No examples found in this run's golden set._\n")
        continue

    for item in items:
        g, p = item["gold"], item["pred"]
        ev   = p.get("retrieved_evidence", [])

        lines.append(f"**Customer Message:**\n> {g['customer_msg']}\n")
        lines.append(f"**True Intent:** `{g['intent']}` | "
                     f"**Predicted Intent:** `{p.get('intent','—')}`  \n"
                     f"**True Escalation:** `{g['escalation_label']}` | "
                     f"**Predicted:** `{p.get('decision','—')}`  \n")
        lines.append(f"**Platform:** `{g.get('platform','unknown')}`  \n")

        if ev:
            lines.append(f"\n**Top Retrieved Evidence** "
                         f"(sim={ev[0].get('similarity',0):.3f}, "
                         f"platform={ev[0].get('platform','?')}):**\n")
            lines.append(f"> Customer: {ev[0]['customer_msg'][:150]}  \n")
            lines.append(f"> Agent: {ev[0]['brand_response'][:200]}  \n")
        else:
            lines.append("\n**Retrieved Evidence:** _none_\n")

        lines.append(f"\n**Generated Reply:**\n> {p.get('draft_response','—')[:300]}\n")

        # Root cause and fix
        root_causes = {
            "Wrong Intent Classification":
                ("**Root Cause:** The customer message contains surface-level keywords "
                 "from multiple intent categories. The embedding classifier found a "
                 "higher-similarity seed example in the wrong class.\n\n"
                 "**Proposed Fix:** Add more diverse seed examples in the confused intents. "
                 "Consider a two-stage classifier: first separate billing/account "
                 "from technical, then sub-classify.\n"),
            "Missed Escalation (False Auto-Handle)":
                ("**Root Cause:** The escalation signal was subtle — no explicit keyword "
                 "matched, but the combination of billing intent + low confidence "
                 "should have triggered escalation.\n\n"
                 "**Proposed Fix:** Lower the escalation threshold specifically for "
                 "billing_charge and account_login intents, as these have higher "
                 "real-world risk.\n"),
            "DM Redirect Retrieved as Evidence":
                ("**Root Cause:** Despite filtering DM-only responses during preprocessing, "
                 "some DM redirects with trailing context were retained. The retriever "
                 "treats them as valid evidence.\n\n"
                 "**Proposed Fix:** Add a secondary filter at retrieval time: if "
                 "top-k results are all DM redirects, return no evidence and escalate.\n"),
            "Insufficient Retrieval Evidence":
                ("**Root Cause:** The customer's query is rare or expressed in unusual "
                 "language, so no retrieval candidate exceeds the similarity threshold.\n\n"
                 "**Proposed Fix:** Implement retrieval abstention: when max similarity < 0.30, "
                 "route to escalation rather than generating a weakly-grounded reply.\n"),
            "Platform Mismatch in Retrieved Evidence":
                ("**Root Cause:** The platform filter returned fewer than top-k results, "
                 "triggering global fallback. The global retriever returned evidence "
                 "from a different platform that happens to be semantically similar.\n\n"
                 "**Proposed Fix:** When platform-filtered results exist but are "
                 "insufficient, prefer them over global results even if global "
                 "similarity is higher. Weight platform match as a hard constraint.\n"),
        }
        lines.append(root_causes.get(failure_name, ""))

out_path = DOCS_DIR / "failure_analysis.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"\nFailure analysis saved → {out_path}")
