"""
ONE-COMMAND FULL PIPELINE.

Runs every step in order and produces all results.
Takes ~10–15 minutes end-to-end (mostly index building + evaluation).

Usage:
  python run_all.py
  python run_all.py --no-llm    # skip LLM judge (no API key needed)
"""

import subprocess, sys, time, json
from pathlib import Path

BASE = Path(__file__).parent
steps = [
    ("Preprocess SpotifyCares",        [sys.executable, str(BASE/"preprocess.py")]),
    ("Build vector index",             [sys.executable, str(BASE/"build_index.py")]),
    ("Build golden set",               [sys.executable, str(BASE/"build_golden_set.py")]),
    ("Run evaluation",                 [sys.executable, str(BASE/"evaluate.py")] +
                                       (["--no-llm"] if "--no-llm" in sys.argv else [])),
    ("Run failure analysis",           [sys.executable, str(BASE/"failure_analysis.py")]),
    ("Generate intent taxonomy doc",   [sys.executable, str(BASE/"write_docs.py")]),
]

SEP = "=" * 60
results = {}
start_total = time.time()

for step_name, cmd in steps:
    print(f"\n{SEP}\n  {step_name}\n{SEP}", flush=True)
    t0 = time.time()
    r  = subprocess.run(cmd, cwd=str(BASE))
    elapsed = time.time() - t0
    ok = r.returncode == 0
    results[step_name] = {"ok": ok, "elapsed": round(elapsed, 1)}
    print(f"  {'OK' if ok else 'FAILED'} ({elapsed:.1f}s)", flush=True)
    if not ok:
        print(f"  Step failed. Check output above.", flush=True)
        break

total = time.time() - start_total
print(f"\n{SEP}")
print(f"  Pipeline complete in {total:.0f}s")
print(SEP)
for name, res in results.items():
    status = "OK" if res["ok"] else "FAILED"
    print(f"  {status:<6}  {name:<40}  ({res['elapsed']}s)")

# Print headline results
res_path = BASE / "results" / "all_results.json"
if res_path.exists():
    data = json.load(open(res_path))
    print(f"\n{'='*60}")
    print("  HEADLINE RESULTS")
    print(f"{'='*60}")
    print(f"  {'Metric':<30} {'Trivial':>8} {'SimpleRAG':>10} {'Final':>8}")
    print("-"*60)
    metrics = [
        ("Intent Macro-F1",       "macro_f1"),
        ("Recall@3",              "recall_at_3"),
        ("Escalation F1",         "esc_f1"),
        ("False Auto-Handle Rate","false_auto_handle_rate"),
    ]
    for label, key in metrics:
        t = data.get("trivial", {}).get(key, "—")
        s = data.get("simple_rag", {}).get(key, "—")
        f = data.get("final", {}).get(key, "—")
        print(f"  {label:<30} {str(t):>8} {str(s):>10} {str(f):>8}")
    if data.get("llm_judge", {}).get("overall"):
        print(f"  {'LLM Judge Overall (1-5)':<30} {'N/A':>8} {'N/A':>10} "
              f"{data['llm_judge']['overall']:>8.3f}")
