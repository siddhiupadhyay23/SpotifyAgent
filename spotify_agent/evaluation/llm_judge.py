"""
LLM-as-Judge Evaluation & Human Agreement Harness for SpotifyCares Support Agent.

Evaluates response quality across 4 dimensions:
1. Groundedness (1-5)
2. Relevance (1-5)
3. Helpfulness (1-5)
4. Overall Quality (1-5)

Evaluates a deterministic 60-example sample from final_golden_set.jsonl.
Crucial Privacy & Isolation Rule:
The judge evaluates ONLY:
- customer_message
- retrieved_evidence
- generated_response
- escalation_decision & reason
The judge NEVER sees human intent or human escalation ground-truth labels.
"""

import os
import sys
import json
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import RANDOM_SEED, JUDGE_SAMPLE_SIZE, LLM_MODEL

GOLDEN_FILE       = ROOT / "golden_set" / "final_golden_set.jsonl"
PREDICTIONS_FILE   = ROOT / "results" / "final_predictions.jsonl"
HUMAN_REVIEW_CSV  = ROOT / "golden_set" / "reply_quality_human_review.csv"
RESULTS_DIR       = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

JUDGE_RESULTS_FILE = RESULTS_DIR / "llm_judge_results.jsonl"
JUDGE_SUMMARY_JSON = RESULTS_DIR / "llm_judge_summary.json"
JUDGE_SUMMARY_MD   = RESULTS_DIR / "llm_judge_summary.md"

RUBRIC_VERSION = "1.0"

SYSTEM_PROMPT = """You are an impartial, expert evaluator of customer support responses for SpotifyCares.
Evaluate the AI draft response based strictly on the customer message, the retrieved historical support evidence, and the escalation state.

Evaluation Rubric (Score 1 to 5 for each):

1. Groundedness (1-5):
   5 = Fully supported: every claim, troubleshooting step, or URL is directly grounded in the retrieved evidence. Zero hallucination.
   4 = Mostly supported: core troubleshooting is grounded; minor polite filler wording without unsupported facts.
   3 = Partially supported: some advice matches evidence, but includes unsupported procedural steps or speculative claims.
   2 = Substantially unsupported: major assertions or steps have no basis in the retrieved evidence.
   1 = Hallucinated: fabricated features, invalid URLs, or claims that contradict evidence.

2. Relevance (1-5):
   5 = Directly targeted: precisely addresses the customer's reported issue and stated platform/device.
   4 = Mostly relevant: addresses the core issue with minor generic troubleshooting.
   3 = Partially relevant: touches problem area but misses key customer complaint or assumes wrong platform.
   2 = Largely irrelevant: latches onto minor keywords rather than customer problem.
   1 = Irrelevant: fails to address the customer's message.

3. Helpfulness (1-5):
   5 = Clear, actionable, and safe: provides crystal-clear guidance and safe escalation routing when needed.
   4 = Useful with minor omissions: helpful but could be slightly clearer on navigation or details.
   3 = Somewhat useful: high-level advice that may require further customer follow-up.
   2 = Limited usefulness: repetitive, vague stock advice that risks frustrating the user.
   1 = Not useful: misleading, confusing, or dangerous advice.

4. Overall Quality (1-5):
   5 = Excellent, production-ready support response.
   4 = Good, safe to send with minor polishing.
   3 = Borderline, generic or impersonal.
   2 = Deficient, requires substantial human revision.
   1 = Unacceptable, inaccurate or unsafe.

Return ONLY a valid JSON object with the following schema:
{
  "groundedness": <integer 1-5>,
  "relevance": <integer 1-5>,
  "helpfulness": <integer 1-5>,
  "overall": <integer 1-5>,
  "rationale": "<concise 1-2 sentence justification>"
}"""


def load_deterministic_sample(sample_size=JUDGE_SAMPLE_SIZE, seed=RANDOM_SEED):
    """Deterministically select sample_size examples from final_golden_set.jsonl."""
    if not GOLDEN_FILE.exists():
        raise FileNotFoundError(f"Golden set file not found: {GOLDEN_FILE}")

    golden = []
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                golden.append(json.loads(line))

    rng = random.Random(seed)
    indices = sorted(rng.sample(range(len(golden)), sample_size))
    sample = [golden[i] for i in indices]
    return sample


def get_predictions_map():
    """Load existing agent predictions mapped by golden_id/example_id."""
    if not PREDICTIONS_FILE.exists():
        return {}
    preds = {}
    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                eid = p.get("golden_id") or p.get("example_id")
                if eid:
                    preds[eid] = p
    return preds


def check_human_ratings():
    """Inspect human review CSV and check if any ratings are populated."""
    if not HUMAN_REVIEW_CSV.exists():
        return {"exists": False, "completed": 0, "total": 0, "rows": []}

    import csv
    completed = 0
    total = 0
    rows = []
    with open(HUMAN_REVIEW_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            scores = [
                row.get("human_groundedness", "").strip(),
                row.get("human_relevance", "").strip(),
                row.get("human_helpfulness", "").strip(),
                row.get("human_overall", "").strip(),
            ]
            if all(s != "" for s in scores):
                try:
                    parsed = [int(s) for s in scores]
                    if all(1 <= s <= 5 for s in parsed):
                        completed += 1
                except ValueError:
                    pass
            rows.append(row)

    return {
        "exists": True,
        "completed": completed,
        "total": total,
        "rows": rows,
    }


def calculate_agreement(judge_results_path=JUDGE_RESULTS_FILE, human_csv_path=HUMAN_REVIEW_CSV):
    """Calculate judge-vs-human agreement statistics if human ratings are present."""
    human_status = check_human_ratings()
    if not human_status["exists"] or human_status["completed"] == 0:
        print("\nHuman review incomplete — agreement not calculated")
        return None

    if not Path(judge_results_path).exists():
        print("\nJudge results not found — agreement not calculated")
        return None

    # Load judge scores
    judge_map = {}
    with open(judge_results_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                if item.get("status") == "success" and "scores" in item:
                    eid = item.get("example_id")
                    judge_map[eid] = item["scores"]

    # Match paired scores
    from sklearn.metrics import cohen_kappa_score
    from scipy.stats import spearmanr

    dims = ["groundedness", "relevance", "helpfulness", "overall"]
    paired = {d: {"human": [], "judge": []} for d in dims}

    for row in human_status["rows"]:
        eid = row.get("example_id")
        if eid in judge_map:
            try:
                h_g = int(row["human_groundedness"])
                h_r = int(row["human_relevance"])
                h_h = int(row["human_helpfulness"])
                h_o = int(row["human_overall"])
                j_scores = judge_map[eid]
                paired["groundedness"]["human"].append(h_g)
                paired["groundedness"]["judge"].append(int(j_scores["groundedness"]))
                paired["relevance"]["human"].append(h_r)
                paired["relevance"]["judge"].append(int(j_scores["relevance"]))
                paired["helpfulness"]["human"].append(h_h)
                paired["helpfulness"]["judge"].append(int(j_scores["helpfulness"]))
                paired["overall"]["human"].append(h_o)
                paired["overall"]["judge"].append(int(j_scores["overall"]))
            except (ValueError, KeyError):
                continue

    n_paired = len(paired["overall"]["human"])
    if n_paired == 0:
        print("\nHuman review incomplete — agreement not calculated")
        return None

    agreement = {"n_paired": n_paired, "metrics": {}}
    print(f"\nEvaluating Judge-Human Agreement on {n_paired} paired examples:")
    for d in dims:
        h = paired[d]["human"]
        j = paired[d]["judge"]
        try:
            qwk = cohen_kappa_score(h, j, weights="quadratic")
        except Exception:
            qwk = float("nan")
        try:
            spr, _ = spearmanr(h, j)
        except Exception:
            spr = float("nan")

        agreement["metrics"][d] = {
            "quadratic_weighted_kappa": round(float(qwk), 4),
            "spearman_rho": round(float(spr), 4),
        }
        print(f"  {d:<15} Quadratic Weighted Kappa = {qwk:.4f}  Spearman rho = {spr:.4f}")

    return agreement


def run_judge_evaluation(sample, predictions):
    """Execute LLM-as-judge evaluation if API key is present."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        print("\nLLM execution: BLOCKED — OPENAI_API_KEY not configured")
        print("Rubric, deterministic sample, and human review template are fully prepared.")
        return {
            "status": "blocked",
            "reason": "OPENAI_API_KEY not configured",
            "sample_size": len(sample),
            "scored_count": 0,
        }

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    from retriever import retrieve_similar

    print(f"\nRunning LLM-as-Judge evaluation on {len(sample)} examples using {LLM_MODEL}...")
    results = []
    failed_calls = []

    for i, item in enumerate(sample, 1):
        eid = item["example_id"]
        c_msg = item.get("customer_message") or item.get("customer_msg", "")
        pred = predictions.get(eid, {})
        draft = pred.get("draft_reply", "")
        esc_decision = pred.get("pred_escalation", "AUTO_HANDLE")
        esc_reason = pred.get("escalation_reason", "")
        plat = pred.get("pred_platform", "unknown")

        # Retrieve evidence directly to ensure judge has full context
        evidence_items = retrieve_similar(c_msg, top_k=3)
        ev_text = ""
        for idx, ev in enumerate(evidence_items, 1):
            ev_text += (
                f"\n[{idx}] Score={ev.get('score', 0):.3f} (Platform: {ev.get('platform','unknown')}):\n"
                f"     Customer: {ev.get('customer_msg','')[:120]}\n"
                f"     Resolution: {ev.get('brand_response','')[:150]}\n"
            )

        user_content = (
            f"Customer Message:\n\"{c_msg}\"\n\n"
            f"Detected Platform: {plat}\n"
            f"Escalation Decision: {esc_decision} (Reason: {esc_reason})\n\n"
            f"Retrieved Historical Evidence:{ev_text if ev_text else ' None'}\n\n"
            f"Draft Reply to Evaluate:\n\"{draft}\"\n\n"
            f"Evaluate the draft reply strictly on the 1-5 scale for Groundedness, Relevance, Helpfulness, and Overall Quality."
        )

        record = {
            "example_id": eid,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": LLM_MODEL,
            "rubric_version": RUBRIC_VERSION,
            "customer_message": c_msg,
            "draft_reply": draft,
            "escalation_decision": esc_decision,
        }

        try:
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content
            parsed = json.loads(raw_content)

            record["status"] = "success"
            record["raw_response"] = raw_content
            record["scores"] = {
                "groundedness": int(parsed["groundedness"]),
                "relevance": int(parsed["relevance"]),
                "helpfulness": int(parsed["helpfulness"]),
                "overall": int(parsed["overall"]),
            }
            record["rationale"] = parsed.get("rationale", "")
            results.append(record)
            print(f"  [{i}/{len(sample)}] {eid}: Groundedness={record['scores']['groundedness']} Relevance={record['scores']['relevance']} Helpfulness={record['scores']['helpfulness']} Overall={record['scores']['overall']}")

        except Exception as e:
            record["status"] = "error"
            record["error"] = str(e)
            results.append(record)
            failed_calls.append({"example_id": eid, "error": str(e)})
            print(f"  [{i}/{len(sample)}] {eid}: FAILED ({e})")

    # Save raw results
    with open(JUDGE_RESULTS_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Compute summary
    valid_scores = [r["scores"] for r in results if r.get("status") == "success"]
    n_valid = len(valid_scores)

    summary = {
        "n_evaluated": len(sample),
        "n_success": n_valid,
        "n_failed": len(failed_calls),
        "model": LLM_MODEL,
        "rubric_version": RUBRIC_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "failed_calls": failed_calls,
    }

    if n_valid > 0:
        for dim in ["groundedness", "relevance", "helpfulness", "overall"]:
            vals = [s[dim] for s in valid_scores]
            mean_val = sum(vals) / n_valid
            dist = {str(k): vals.count(k) for k in range(1, 6)}
            summary[f"mean_{dim}"] = round(mean_val, 4)
            summary[f"{dim}_distribution"] = dist

    with open(JUDGE_SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Markdown summary
    md_content = f"""# LLM-as-Judge Evaluation Summary

**Model:** `{LLM_MODEL}`  
**Rubric Version:** `{RUBRIC_VERSION}`  
**Date:** `{summary['timestamp']}`  
**Sample Size:** {len(sample)}  
**Successful Evaluations:** {n_valid}  
**Failed Calls:** {len(failed_calls)}  

---

## Mean Dimensions (1–5)

| Dimension | Mean Score | 1s | 2s | 3s | 4s | 5s |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Groundedness** | {summary.get('mean_groundedness', 'N/A')} | {summary.get('groundedness_distribution',{}).get('1',0)} | {summary.get('groundedness_distribution',{}).get('2',0)} | {summary.get('groundedness_distribution',{}).get('3',0)} | {summary.get('groundedness_distribution',{}).get('4',0)} | {summary.get('groundedness_distribution',{}).get('5',0)} |
| **Relevance** | {summary.get('mean_relevance', 'N/A')} | {summary.get('relevance_distribution',{}).get('1',0)} | {summary.get('relevance_distribution',{}).get('2',0)} | {summary.get('relevance_distribution',{}).get('3',0)} | {summary.get('relevance_distribution',{}).get('4',0)} | {summary.get('relevance_distribution',{}).get('5',0)} |
| **Helpfulness** | {summary.get('mean_helpfulness', 'N/A')} | {summary.get('helpfulness_distribution',{}).get('1',0)} | {summary.get('helpfulness_distribution',{}).get('2',0)} | {summary.get('helpfulness_distribution',{}).get('3',0)} | {summary.get('helpfulness_distribution',{}).get('4',0)} | {summary.get('helpfulness_distribution',{}).get('5',0)} |
| **Overall Quality** | {summary.get('mean_overall', 'N/A')} | {summary.get('overall_distribution',{}).get('1',0)} | {summary.get('overall_distribution',{}).get('2',0)} | {summary.get('overall_distribution',{}).get('3',0)} | {summary.get('overall_distribution',{}).get('4',0)} | {summary.get('overall_distribution',{}).get('5',0)} |

---
"""
    with open(JUDGE_SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"Saved judge results -> {JUDGE_RESULTS_FILE.relative_to(ROOT)}")
    print(f"Saved judge summary -> {JUDGE_SUMMARY_JSON.relative_to(ROOT)}")
    print(f"Saved judge summary markdown -> {JUDGE_SUMMARY_MD.relative_to(ROOT)}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="LLM-as-Judge reply quality evaluation harness")
    parser.add_argument("--agreement-only", action="store_true", help="Only check judge-human agreement")
    args = parser.parse_args()

    sample = load_deterministic_sample()
    print(f"Loaded {len(sample)} deterministic sample examples (Random Seed: {RANDOM_SEED})")

    if args.agreement_only:
        calculate_agreement()
        return

    predictions = get_predictions_map()
    judge_res = run_judge_evaluation(sample, predictions)
    calculate_agreement()


if __name__ == "__main__":
    main()
