"""Compare Jaccard vs Hybrid on 20 golden examples."""
import json, sys, re
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from retriever import retrieve_similar              # jaccard baseline
from retrieval.hybrid_retriever import retrieve_hybrid   # new hybrid

GOLDEN = ROOT / "golden_set" / "golden_set.jsonl"

# load first 20
golden = []
with open(GOLDEN, encoding="utf-8") as f:
    for line in f:
        golden.append(json.loads(line))
        if len(golden) == 20:
            break

# ── metrics helper ────────────────────────────────────────────────
def metrics(results_list):
    cov  = sum(1 for r in results_list if r and r[0]["score"] > 0.15) / len(results_list)
    avg  = sum(r[0]["score"] for r in results_list if r) / max(sum(1 for r in results_list if r), 1)
    plat = sum(1 for r in results_list if r and r[0].get("platform_match", False)) / len(results_list)
    return {"coverage_gt15": round(cov,4), "avg_top1": round(avg,4), "platform_match": round(plat,4)}

jac_results = []
hyb_results = []

for g in golden:
    msg  = g["customer_msg"]
    plat = g.get("platform","unknown")
    jac_results.append(retrieve_similar(msg, top_k=3, platform_filter=plat))
    hyb_results.append(retrieve_hybrid(msg, top_k=3))

jac_m = metrics(jac_results)
hyb_m = metrics(hyb_results)

print("RETRIEVAL COMPARISON (n=20 golden examples)")
print(f"{'Metric':<30} {'Jaccard':>10}  {'Hybrid':>10}  {'Delta':>8}")
print("-" * 62)
for k in ["coverage_gt15","avg_top1","platform_match"]:
    d = hyb_m[k] - jac_m[k]
    print(f"  {k:<28} {jac_m[k]:>10.4f}  {hyb_m[k]:>10.4f}  {d:>+8.4f}")

# ── 3 examples where top-1 differs ───────────────────────────────
print("\n--- Examples where hybrid top-1 differs from Jaccard ---")
shown = 0
for i, g in enumerate(golden):
    jr = jac_results[i]
    hr = hyb_results[i]
    if not jr or not hr:
        continue
    if jr[0]["customer_msg"] != hr[0]["customer_msg"] and shown < 3:
        shown += 1
        print(f"\n[{g['golden_id']}] Customer: {g['customer_msg'][:90]}")
        print(f"  Jaccard top-1  (score={jr[0]['score']:.3f}): {jr[0]['customer_msg'][:70]}")
        print(f"    -> {jr[0]['brand_response'][:80]}")
        print(f"  Hybrid  top-1  (score={hr[0]['score']:.3f}): {hr[0]['customer_msg'][:70]}")
        print(f"    -> {hr[0]['brand_response'][:80]}")

if shown == 0:
    print("  (top-1 identical for all 20 examples on this sample)")

print("\nDONE. Stopping.")
