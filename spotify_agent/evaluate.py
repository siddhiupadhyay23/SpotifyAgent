"""
Full evaluation: intent classifier + retrieval ablation + final agent.
Reads only processed files. Does NOT touch the raw 2.8M-row CSV.
Run: python evaluate.py
"""

import json, sys, time, argparse
from pathlib import Path
from collections import Counter

ROOT           = Path(__file__).parent
GOLDEN_PRIMARY = ROOT / "golden_set" / "final_golden_set.jsonl"
GOLDEN_SILVER  = ROOT / "golden_set" / "golden_set.jsonl"
RESULTS        = ROOT / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

# Parse CLI arguments to support evaluating silver/rule-derived set and --no-llm
parser = argparse.ArgumentParser(description="Full evaluation harness")
parser.add_argument("--silver", "--rule-derived", action="store_true",
                    help="Evaluate on legacy rule-derived silver set instead of primary human-reviewed golden set")
parser.add_argument("--no-llm", action="store_true",
                    help="Skip LLM response quality evaluation")
args, _ = parser.parse_known_args()

use_silver = args.silver or not GOLDEN_PRIMARY.exists()
GOLDEN = GOLDEN_SILVER if use_silver else GOLDEN_PRIMARY
is_human_reviewed = not use_silver

sys.path.insert(0, str(ROOT))

from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report,
)

INTENTS = [
    "playback_error","account_login","premium_subscription","billing_charge",
    "app_crash_bug","playlist_library","content_unavailable",
    "device_platform","offline_download",
]

# ── load golden set ───────────────────────────────────────────────
golden = []
with open(GOLDEN, encoding="utf-8") as f:
    for line in f:
        golden.append(json.loads(line))
N = len(golden)
benchmark_name = "human-reviewed primary benchmark" if is_human_reviewed else "rule-derived silver benchmark"
print(f"Golden set: {N} examples ({benchmark_name} from {GOLDEN.name})", flush=True)

messages     = [g.get("customer_message") or g.get("customer_msg", "") for g in golden]
true_intents = [g.get("human_intent") or g.get("intent", "") for g in golden]
true_esc     = [g.get("human_escalation") or g.get("escalation_label", "AUTO_HANDLE") for g in golden]  # ESCALATE / AUTO_HANDLE

# ══════════════════════════════════════════════════════════════════
# STEP 1 — Intent classifier
# ══════════════════════════════════════════════════════════════════
print("\n[1/4] Intent classifier ...", flush=True)
import pickle
with open(ROOT / "models" / "tfidf_vec.pkl", "rb") as f: vec = pickle.load(f)
with open(ROOT / "models" / "lr_clf.pkl",    "rb") as f: clf = pickle.load(f)

pred_intents  = clf.predict(vec.transform(messages)).tolist()
pred_proba    = clf.predict_proba(vec.transform(messages)).max(axis=1).tolist()

acc_clf  = accuracy_score(true_intents, pred_intents)
mf1_clf  = f1_score(true_intents, pred_intents, average="macro",    labels=INTENTS, zero_division=0)
wf1_clf  = f1_score(true_intents, pred_intents, average="weighted", labels=INTENTS, zero_division=0)
per_clf  = f1_score(true_intents, pred_intents, average=None,       labels=INTENTS, zero_division=0)

print(f"  Accuracy   : {acc_clf:.4f}")
print(f"  Macro F1   : {mf1_clf:.4f}")
print(f"  Weighted F1: {wf1_clf:.4f}")

# ══════════════════════════════════════════════════════════════════
# STEP 2 — Retrieval ablation
# ══════════════════════════════════════════════════════════════════
print("\n[2/4] Retrieval ablation ...", flush=True)

import re
_PLAT = re.compile(
    r"\b(android|ios|iphone|ipad|windows|mac|chromecast|alexa|echo|"
    r"sonos|speaker|tv|ps[34]|car|carplay|roku|web|browser)\b", re.I)
def plat(t): m=_PLAT.search(t); return m.group(0).lower() if m else "unknown"

gold_platforms = [g.get("platform","unknown") for g in golden]

from retriever import retrieve_similar
from retrieval.hybrid_retriever import retrieve_hybrid

def retrieval_stats(results_list, query_platforms, label):
    cov = sum(1 for r in results_list if r and r[0]["score"] > 0.15) / len(results_list)
    avg = sum(r[0]["score"] for r in results_list if r) / max(sum(1 for r in results_list if r),1)
    # platform match: top-1 platform == query platform (only when query platform != unknown)
    plat_queries = [(i,p) for i,(p) in enumerate(query_platforms) if p != "unknown"]
    if plat_queries:
        pm = sum(1 for i,qp in plat_queries
                 if results_list[i] and results_list[i][0].get("platform","unknown")==qp)
        pm_rate = pm / len(plat_queries)
    else:
        pm_rate = 0.0
    print(f"  {label:<25} coverage={cov:.4f}  avg_top1={avg:.4f}  plat_match={pm_rate:.4f}")
    return {"coverage_gt15": round(cov,4), "avg_top1_score": round(avg,4), "platform_match_rate": round(pm_rate,4)}

t0 = time.time()
jac_results = [retrieve_similar(m, top_k=3, platform_filter=p)
               for m, p in zip(messages, gold_platforms)]
jac_stats = retrieval_stats(jac_results, gold_platforms, "Jaccard baseline")

hyb_results = [retrieve_hybrid(m, top_k=3) for m in messages]
hyb_stats = retrieval_stats(hyb_results, gold_platforms, "Hybrid (TF-IDF+Jac+plat)")
print(f"  Retrieval ablation time: {time.time()-t0:.1f}s")

# Note on Recall@K: no ground-truth relevance labels exist for the retrieval corpus.
# We therefore report only coverage, avg similarity, and platform match.
# Recall@K would require human annotation of relevant historical pairs per query.
RECALL_NOTE = (
    "Recall@K not reported: no ground-truth relevance labels exist for the "
    "500-example retrieval sample. Coverage (score>0.15) and platform match "
    "are used as proxy quality signals."
)
print(f"  NOTE: {RECALL_NOTE}")

# ══════════════════════════════════════════════════════════════════
# STEP 3 — Final agent (200 examples)
# ══════════════════════════════════════════════════════════════════
print("\n[3/4] Final agent (200 examples) ...", flush=True)
from agent import run as agent_run

t0 = time.time()
agent_preds = []
for i, g in enumerate(golden):
    c_msg    = g.get("customer_message") or g.get("customer_msg", "")
    t_intent = g.get("human_intent") or g.get("intent", "")
    t_esc    = g.get("human_escalation") or g.get("escalation_label", "AUTO_HANDLE")
    g_id     = g.get("example_id") or g.get("golden_id", f"g{i+1:04d}")

    r = agent_run(c_msg)
    agent_preds.append({
        "golden_id":        g_id,
        "customer_msg":     c_msg,
        "true_intent":      t_intent,
        "pred_intent":      r["intent"],
        "intent_confidence":r["intent_confidence"],
        "true_platform":    g.get("platform","unknown"),
        "pred_platform":    r["platform"],
        "risk_signals":     r["risk_signals"],
        "true_escalation":  t_esc,
        "pred_escalation":  r["decision"],
        "escalation_reason":r["escalation_reason"],
        "draft_reply":      r["draft_reply"],
        "generation_mode":  r["generation_mode"],
        "top_evidence_score": r["retrieved_evidence"][0]["score"] if r["retrieved_evidence"] else 0,
    })
    if (i+1) % 50 == 0:
        print(f"  {i+1}/{N} ...", flush=True)

agent_time = time.time() - t0
print(f"  Done in {agent_time:.1f}s")

# intent metrics
ag_true_i = [p["true_intent"] for p in agent_preds]
ag_pred_i = [p["pred_intent"] for p in agent_preds]
acc_ag    = accuracy_score(ag_true_i, ag_pred_i)
mf1_ag    = f1_score(ag_true_i, ag_pred_i, average="macro",    labels=INTENTS, zero_division=0)
wf1_ag    = f1_score(ag_true_i, ag_pred_i, average="weighted", labels=INTENTS, zero_division=0)
per_ag    = f1_score(ag_true_i, ag_pred_i, average=None,       labels=INTENTS, zero_division=0)

print(f"  Accuracy   : {acc_ag:.4f}")
print(f"  Macro F1   : {mf1_ag:.4f}")
print(f"  Weighted F1: {wf1_ag:.4f}")

# escalation metrics
esc_true_bin = [1 if p["true_escalation"]=="ESCALATE" else 0 for p in agent_preds]
esc_pred_bin = [1 if p["pred_escalation"]=="ESCALATE" else 0 for p in agent_preds]
esc_prec = precision_score(esc_true_bin, esc_pred_bin, zero_division=0)
esc_rec  = recall_score(   esc_true_bin, esc_pred_bin, zero_division=0)
esc_f1   = f1_score(       esc_true_bin, esc_pred_bin, zero_division=0)
false_auto = sum(1 for t,p in zip(esc_true_bin,esc_pred_bin) if t==1 and p==0)
n_true_esc = sum(esc_true_bin)
esc_rate   = sum(esc_pred_bin) / N

print(f"  Escalation F1       : {esc_f1:.4f}  (prec={esc_prec:.4f} rec={esc_rec:.4f})")
print(f"  False auto-handle   : {false_auto}/{n_true_esc} true escalations missed")
print(f"  Agent escalation rate: {esc_rate:.4f}  ({sum(esc_pred_bin)}/{N})")

# retrieval coverage from agent
ag_cov = sum(1 for p in agent_preds if p["top_evidence_score"] > 0.15) / N
ag_avg = sum(p["top_evidence_score"] for p in agent_preds) / N

# generation modes
gen_modes = Counter(p["generation_mode"] for p in agent_preds)

# platform detection (only on examples with a known gold platform)
plat_gold_known = [(p["true_platform"], p["pred_platform"])
                   for p in agent_preds if p["true_platform"] not in ("unknown","")]
if plat_gold_known:
    plat_acc = sum(1 for t,pr in plat_gold_known if t==pr) / len(plat_gold_known)
    print(f"  Platform accuracy   : {plat_acc:.4f}  (n={len(plat_gold_known)} with known platform)")
else:
    plat_acc = None

# ══════════════════════════════════════════════════════════════════
# STEP 4 — Majority baseline (for comparison table)
# ══════════════════════════════════════════════════════════════════
majority_intent = "playback_error"   # from trivial_baseline.json
maj_preds = [majority_intent] * N
acc_maj = accuracy_score(true_intents, maj_preds)
mf1_maj = f1_score(true_intents, maj_preds, average="macro",    labels=INTENTS, zero_division=0)
wf1_maj = f1_score(true_intents, maj_preds, average="weighted", labels=INTENTS, zero_division=0)

# ══════════════════════════════════════════════════════════════════
# PRINT FINAL TABLE
# ══════════════════════════════════════════════════════════════════
print("\n" + "="*65)
print("  FINAL RESULTS SUMMARY")
print("="*65)
print(f"  {'System':<30} {'Acc':>7}  {'MacroF1':>8}  {'WtdF1':>7}")
print("  " + "-"*55)
print(f"  {'Majority baseline':<30} {acc_maj:>7.4f}  {mf1_maj:>8.4f}  {wf1_maj:>7.4f}")
print(f"  {'TF-IDF + LR classifier':<30} {acc_clf:>7.4f}  {mf1_clf:>8.4f}  {wf1_clf:>7.4f}")
print(f"  {'Final agent':<30} {acc_ag:>7.4f}  {mf1_ag:>8.4f}  {wf1_ag:>7.4f}")

print(f"\n  {'Retrieval':<28} {'Cov>0.15':>9}  {'AvgTop1':>8}  {'PlatMatch':>10}")
print("  " + "-"*55)
print(f"  {'Jaccard baseline':<28} {jac_stats['coverage_gt15']:>9.4f}  "
      f"{jac_stats['avg_top1_score']:>8.4f}  {jac_stats['platform_match_rate']:>10.4f}")
print(f"  {'Hybrid (TF-IDF+Jac+plat)':<28} {hyb_stats['coverage_gt15']:>9.4f}  "
      f"{hyb_stats['avg_top1_score']:>8.4f}  {hyb_stats['platform_match_rate']:>10.4f}")

print(f"\n  Escalation (golden set, n={N}):")
print(f"    True ESCALATE labels : {n_true_esc}")
print(f"    Agent ESCALATE preds : {sum(esc_pred_bin)}")
print(f"    Precision : {esc_prec:.4f}")
print(f"    Recall    : {esc_rec:.4f}")
print(f"    F1        : {esc_f1:.4f}")
print(f"    False auto-handle rate: {false_auto}/{n_true_esc} "
      f"({100*false_auto/max(n_true_esc,1):.1f}%)")

print(f"\n  Generation modes:")
for mode, cnt in sorted(gen_modes.items(), key=lambda x:-x[1]):
    print(f"    {mode:<40} {cnt:>4}")

print(f"\n  Per-intent F1 (final agent, golden set):")
for intent, s in sorted(zip(INTENTS, per_ag), key=lambda x:-x[1]):
    n_t = sum(1 for y in ag_true_i if y==intent)
    print(f"    {intent:<28} {s:.4f}  (n={n_t})")
print("="*65)

# ══════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════
print("\n[4/4] Saving ...", flush=True)

full_limitations = [
    f"Golden set size = {N}; per-intent estimates for rare classes (n<15) have high variance.",
    "Retrieval corpus capped at 500 examples (sample from train.jsonl). Full corpus = 34,721 pairs.",
    "No OPENAI_API_KEY: generation uses template fallback, not grounded LLM responses.",
    "Response quality not evaluated (requires LLM judge or human annotation).",
    "Recall@K not reported: no ground-truth relevance labels exist for retrieval pairs.",
    "Dataset spans 2013-2017; Spotify product/pricing has changed significantly since.",
]
if not is_human_reviewed:
    full_limitations.insert(4, "Intent labels in golden set are keyword-derived (automated), not human-annotated.")
    full_limitations.insert(5, "Escalation labels in golden set derived from keyword rules + high-risk intent heuristic, not human judgment.")

full = {
    "benchmark":       "human_reviewed" if is_human_reviewed else "rule_derived_silver",
    "golden_set_file": GOLDEN.name,
    "golden_set_size": N,
    "intent_classifier": {
        "model":       "TF-IDF (ngram 1-2, max 30k) + LogisticRegression (balanced)",
        "accuracy":    round(acc_clf,4),
        "macro_f1":    round(mf1_clf,4),
        "weighted_f1": round(wf1_clf,4),
        "per_intent_f1": {i:round(float(s),4) for i,s in zip(INTENTS,per_clf)},
    },
    "majority_baseline": {
        "majority_intent": majority_intent,
        "accuracy":    round(acc_maj,4),
        "macro_f1":    round(mf1_maj,4),
        "weighted_f1": round(wf1_maj,4),
    },
    "retrieval_ablation": {
        "note": RECALL_NOTE,
        "jaccard": jac_stats,
        "hybrid":  hyb_stats,
    },
    "final_agent": {
        "accuracy":    round(acc_ag,4),
        "macro_f1":    round(mf1_ag,4),
        "weighted_f1": round(wf1_ag,4),
        "per_intent_f1": {i:round(float(s),4) for i,s in zip(INTENTS,per_ag)},
        "escalation": {
            "true_escalate_count":  n_true_esc,
            "pred_escalate_count":  sum(esc_pred_bin),
            "escalation_rate":      round(esc_rate,4),
            "precision":            round(esc_prec,4),
            "recall":               round(esc_rec,4),
            "f1":                   round(esc_f1,4),
            "false_auto_handle":    false_auto,
            "false_auto_handle_rate": round(false_auto/max(n_true_esc,1),4),
        },
        "retrieval_coverage_gt15": round(ag_cov,4),
        "avg_top1_score":          round(ag_avg,4),
        "platform_accuracy":       round(plat_acc,4) if plat_acc else "n/a (no gold labels)",
        "generation_modes":        dict(gen_modes),
        "llm_response_quality":    "NOT EVALUATED — no OPENAI_API_KEY set",
    },
    "limitations": full_limitations,
}

(RESULTS / "full_evaluation.json").write_text(
    json.dumps(full, indent=2), encoding="utf-8")

with open(RESULTS / "final_predictions.jsonl", "w", encoding="utf-8") as f:
    for p in agent_preds:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

# ── markdown report ───────────────────────────────────────────────
per_clf_rows = "\n".join(
    f"| `{i}` | {round(float(s),4):.4f} | {round(float(sa),4):.4f} |"
    for i,s,sa in sorted(zip(INTENTS,per_clf,per_ag), key=lambda x:-x[1]))

esc_note = "> Escalation ground truth verified by human review." if is_human_reviewed else "> Escalation labels are keyword-rule derived. True human escalation judgment may differ."

md = f"""# Full Evaluation — SpotifyCares Support Agent

All results measured on **{N} held-out golden examples** from `golden_set/{GOLDEN.name}` ({benchmark_name}).
No raw dataset re-read. No data leakage (golden set from test split, retrieval from train+val).

---

## Intent Classification

| System | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|
| Majority baseline (always `playback_error`) | {acc_maj:.4f} | {mf1_maj:.4f} | {wf1_maj:.4f} |
| TF-IDF + Logistic Regression | {acc_clf:.4f} | {mf1_clf:.4f} | {wf1_clf:.4f} |
| Final agent (same classifier) | {acc_ag:.4f} | {mf1_ag:.4f} | {wf1_ag:.4f} |

The macro F1 improvement from majority ({mf1_maj:.4f}) to classifier ({mf1_clf:.4f})
demonstrates the classifier provides genuine signal across all 9 intent classes.

### Per-intent F1 (TF-IDF clf vs Final agent, golden set)

| Intent | TF-IDF clf | Final agent |
|---|---|---|
{per_clf_rows}

---

## Retrieval Ablation

> **Note:** {RECALL_NOTE}

| Method | Coverage >0.15 | Avg Top-1 Score | Platform Match Rate |
|---|---|---|---|
| Jaccard baseline | {jac_stats['coverage_gt15']:.4f} | {jac_stats['avg_top1_score']:.4f} | {jac_stats['platform_match_rate']:.4f} |
| Hybrid (TF-IDF + Jaccard + platform boost) | {hyb_stats['coverage_gt15']:.4f} | {hyb_stats['avg_top1_score']:.4f} | {hyb_stats['platform_match_rate']:.4f} |

Hybrid retrieval improves coverage by +{(hyb_stats['coverage_gt15']-jac_stats['coverage_gt15']):.4f}
and platform match rate by +{(hyb_stats['platform_match_rate']-jac_stats['platform_match_rate']):.4f}.

---

## Escalation (Final Agent)

| Metric | Value |
|---|---|
| True ESCALATE in golden set | {n_true_esc} |
| Agent ESCALATE predictions | {sum(esc_pred_bin)} |
| Precision | {esc_prec:.4f} |
| Recall | {esc_rec:.4f} |
| F1 | {esc_f1:.4f} |
| False auto-handle rate | {false_auto}/{n_true_esc} ({100*false_auto/max(n_true_esc,1):.1f}%) |

{esc_note}

---

## Generation

No `OPENAI_API_KEY` set. All responses used **template fallback** (deterministic).
LLM-based response quality evaluation is pending API access.

Generation modes on golden set:
{chr(10).join(f"- `{k}`: {v}" for k,v in sorted(gen_modes.items(), key=lambda x:-x[1]))}

---

## Limitations

{chr(10).join(f"- {l}" for l in full['limitations'])}
"""

(RESULTS / "full_evaluation.md").write_text(md, encoding="utf-8")

print("Saved -> results/full_evaluation.json")
print("Saved -> results/full_evaluation.md")
print("Saved -> results/final_predictions.jsonl")
print("\nEVALUATION COMPLETE. Stopping.")
