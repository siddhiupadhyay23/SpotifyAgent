# Full Evaluation — SpotifyCares Support Agent

All results measured on **200 held-out golden examples** from `golden_set/golden_set.jsonl`.
No raw dataset re-read. No data leakage (golden set from test split, retrieval from train+val).

---

## Intent Classification

| System | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|
| Majority baseline (always `playback_error`) | 0.1900 | 0.0355 | 0.0607 |
| TF-IDF + Logistic Regression | 0.9050 | 0.8925 | 0.9044 |
| Final agent (same classifier) | 0.9050 | 0.8925 | 0.9044 |

The macro F1 improvement from majority (0.0355) to classifier (0.8925)
demonstrates the classifier provides genuine signal across all 9 intent classes.

### Per-intent F1 (TF-IDF clf vs Final agent, golden set)

| Intent | TF-IDF clf | Final agent |
|---|---|---|
| `billing_charge` | 0.9600 | 0.9600 |
| `account_login` | 0.9375 | 0.9375 |
| `device_platform` | 0.9375 | 0.9375 |
| `offline_download` | 0.9286 | 0.9286 |
| `premium_subscription` | 0.8929 | 0.8929 |
| `playback_error` | 0.8916 | 0.8916 |
| `playlist_library` | 0.8846 | 0.8846 |
| `app_crash_bug` | 0.8000 | 0.8000 |
| `content_unavailable` | 0.8000 | 0.8000 |

---

## Retrieval Ablation

> **Note:** Recall@K not reported: no ground-truth relevance labels exist for the 500-example retrieval sample. Coverage (score>0.15) and platform match are used as proxy quality signals.

| Method | Coverage >0.15 | Avg Top-1 Score | Platform Match Rate |
|---|---|---|---|
| Jaccard baseline | 0.5300 | 0.1761 | 0.5814 |
| Hybrid (TF-IDF + Jaccard + platform boost) | 0.5700 | 0.1782 | 0.4884 |

Hybrid retrieval improves coverage by +0.0400
and platform match rate by +-0.0930.

---

## Escalation (Final Agent)

| Metric | Value |
|---|---|
| True ESCALATE in golden set | 30 |
| Agent ESCALATE predictions | 84 |
| Precision | 0.3214 |
| Recall | 0.9000 |
| F1 | 0.4737 |
| False auto-handle rate | 3/30 (10.0%) |

> Escalation labels are keyword-rule derived. True human escalation judgment may differ.

---

## Generation

No `OPENAI_API_KEY` set. All responses used **template fallback** (deterministic).
LLM-based response quality evaluation is pending API access.

Generation modes on golden set:
- `template_fallback:intent`: 107
- `template_fallback:top_evidence`: 73
- `escalation_override`: 20

---

## Limitations

- Golden set size = 200; per-intent estimates for rare classes (n<15) have high variance.
- Retrieval corpus capped at 500 examples (sample from train.jsonl). Full corpus = 34,721 pairs.
- No OPENAI_API_KEY: generation uses template fallback, not grounded LLM responses.
- Response quality not evaluated (requires LLM judge or human annotation).
- Intent labels in golden set are keyword-derived (automated), not human-annotated.
- Recall@K not reported: no ground-truth relevance labels exist for retrieval pairs.
- Escalation labels in golden set derived from keyword rules + high-risk intent heuristic, not human judgment.
- Dataset spans 2013-2017; Spotify product/pricing has changed significantly since.
