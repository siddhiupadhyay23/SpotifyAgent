# SpotifyCares AI Support Agent

**Hiver SDE Intern Take-Home Assignment**

An evidence-grounded AI support agent for SpotifyCares that classifies incoming customer
messages, retrieves similar historical conversations, generates a contextually grounded reply,
and decides whether to auto-handle the request or escalate to a human agent — with a stated
reason for every decision.

---

## 1. Problem Framing

Customer support teams receive high volumes of repetitive requests that have been solved
before. The core problem: **how do you make an AI agent that knows what worked last time?**

The agent must:

1. Classify the incoming customer message into a support intent
2. Find historically similar cases from the brand's own resolved conversations
3. Draft a response grounded in those historical resolutions
4. Decide whether to auto-handle or escalate, with a defensible reason

---

## 2. Why SpotifyCares

SpotifyCares was selected after measuring all serious candidates in the dataset
against 18 criteria. The final decision between XboxSupport and SpotifyCares was
made on actual measured data — not estimates.

| Metric | XboxSupport | SpotifyCares |
|---|---|---|
| Outbound tweets | 24,557 | **43,265** |
| Paired inbound tweets | 20,213 | **41,585** |
| Reconstructed conversations | 13,504 | **28,281** |
| Useful retrieval pairs | 10,566 | **23,675** |
| DM-redirect rate | **20.8%** | 30.1% |
| Useful response rate | **54.8%** | 47.5% |

Xbox error codes appeared in only 0.86% of customer messages — too rare to justify a
special architecture. SpotifyCares provided 2× more retrieval evidence and 2× more
useful threads for golden-set construction.

**The primary technical differentiator:** SpotifyCares customers frequently mention their
device or platform (iOS, Android, Alexa, TV, Car). The same underlying issue — e.g.
"app keeps stopping" — has materially different resolutions on different platforms.
This justifies platform-aware retrieval as a measurable improvement over naive semantic
similarity.

---

## 3. Dataset and Preprocessing

**Dataset:** [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter)
— 2,811,774 tweets across 108 brand accounts.

**SpotifyCares statistics:**

| Metric | Value |
|---|---|
| Outbound (agent) tweets | 43,265 |
| Paired inbound (customer) tweets | 41,585 |
| Unique customers served | 27,793 |
| Date range | 2013-09-18 → 2017-12-03 |
| Pairs before DM filter | 43,092 |
| DM-only responses dropped | 2,243 (5.2%) |
| Useful pairs kept | 40,849 |

**Temporal split (no random shuffle):**

| Split | Pairs | Date range |
|---|---|---|
| Train | 28,594 | 2013-09 → 2017-11-15 |
| Validation | 6,127 | 2017-11-15 → 2017-11-25 |
| Test (golden pool) | 6,128 | 2017-11-25 → 2017-12-03 |
| Retrieval corpus (train+val) | 34,721 | — |

A temporal split prevents leakage: the agent cannot retrieve a golden-set conversation
because it was in the retrieval corpus. This is verified — 0 overlapping conversation IDs.

**DM filter:** Responses consisting solely of a DM redirect with no troubleshooting content
were dropped from the retrieval corpus. Retained DM redirects that contained meaningful
context were kept. This was an explicit engineering decision (see Decision Log).

---

## 4. Intent Taxonomy

Derived from 28,594 training messages using BERTopic/LDA topic analysis, confirmed by
keyword frequency analysis. All 9 intents are semantically distinct and naturally emerge
from the data.

| # | Intent | Definition | Train Count | Train % | Escalation Policy |
|---|---|---|---|---|---|
| 1 | `playback_error` | Song/music won't play, buffering, skipping, pausing | 2,478 | 8.7% | AUTO_HANDLE |
| 2 | `device_platform` | Spotify not working on a specific device (speaker, TV, car, OS) | 2,160 | 7.6% | AUTO_HANDLE |
| 3 | `premium_subscription` | Plan status, cancellation, trial, plan type | 1,943 | 6.8% | AUTO_HANDLE (ESCALATE if billing dispute) |
| 4 | `playlist_library` | Playlists or saved songs missing, deleted, not syncing | 1,712 | 6.0% | AUTO_HANDLE (ESCALATE if data loss) |
| 5 | `billing_charge` | Unexpected charges, payment failures, refund requests | 1,613 | 5.6% | ESCALATE for disputes |
| 6 | `account_login` | Login failures, password reset, locked account | 1,077 | 3.8% | ESCALATE if security signal |
| 7 | `offline_download` | Downloaded songs unavailable offline, download failures | 848 | 3.0% | AUTO_HANDLE |
| 8 | `content_unavailable` | Songs/artists unavailable due to region/licensing | 699 | 2.4% | AUTO_HANDLE |
| 9 | `app_crash_bug` | App crashes, freezes, black screen, won't open | 614 | 2.1% | AUTO_HANDLE |

Full definitions and escalation policies: `docs/intent_taxonomy.json`, `docs/intent_taxonomy.md`

---

## 5. System Architecture

```
Customer Message
       │
       ▼
TF-IDF + Logistic Regression Intent Classifier
  └── trained on 13,144 keyword-matched training examples
  └── 9-class, balanced weights, ngram (1,2), max 30k features
       │
       ▼
Platform / Device Extraction  (regex, 9 platform types)
  └── android, ios, windows, mac, alexa, sonos, tv, car, web
       │
       ▼
Risk Detection  (keyword rules)
  └── billing_dispute, account_compromise, legal_threat, urgency
       │
       ├── Hard escalation signals → skip retrieval, escalate immediately
       │
       ▼
Hybrid Historical Retrieval
  └── 70% TF-IDF cosine + 20% Jaccard + 10% platform match
  └── Corpus: 34,721 (train+val) pairs
  └── Currently evaluated on 500-example sample (see Limitations)
       │
       ▼
Grounded Response Generation
  └── Template fallback (no LLM API key available — see Limitations)
  └── Uses top-retrieved historical response when useful
  └── Architecture supports gpt-4o-mini via OPENAI_API_KEY env var
       │
       ▼
Confidence + Evidence-Based Escalation Decision
  └── Threshold: confidence < 0.40 → ESCALATE
  └── Threshold: best retrieval score < 0.12 → ESCALATE
  └── High-risk intent with low confidence → ESCALATE
  └── Every escalation includes a stated reason
       │
       ▼
Output: { intent, confidence, platform, response, decision, reason, evidence }
```

---

## 6. Evaluation Methodology

**Golden set:** 200 examples sampled from the temporal test holdout (2017-11-25 to 2017-12-03).
Stratified by intent proportional to training frequency. Includes deliberate over-sampling of
hard/escalation-sensitive examples (≈25% hard, ≈15% escalation-signal examples).

**⚠ Critical disclosure:** The golden set labels are **Kiro-proposed semantic labels**
(`label_source = "kiro_proposed"`, `human_verified = false`). They were generated by
a semantic keyword classifier, not by independent human annotators. This limits the
reliability of the evaluation — see *"What is misleading about my headline number?"* below.

**Leakage check:** 0 overlapping conversation IDs between golden set and retrieval corpus.
Temporal split enforces strict holdout.

**Three systems evaluated:**

| System | Description |
|---|---|
| Trivial baseline | Always predicts majority intent (`playback_error`); fixed template reply |
| TF-IDF + LR | Embedding-free supervised classifier; same classifier used in final agent |
| Final hybrid agent | Classifier + platform extraction + hybrid retrieval + escalation policy |

---

## 7. Results

### Intent Classification

| System | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|
| **Trivial baseline** (majority class) | 19.00% | 3.55% | 6.07% |
| **TF-IDF + LR** | 90.50% | 89.25% | 90.44% |
| **Final agent** | 90.50% | 89.25% | 90.44% |

Macro F1 improvement from trivial to final: **0.0355 → 0.8925 (+25×)**

### Per-Intent F1 (Final Agent, Golden Set)

| Intent | F1 | n |
|---|---|---|
| `billing_charge` | 0.9600 | 25 |
| `account_login` | 0.9375 | 16 |
| `device_platform` | 0.9375 | 33 |
| `offline_download` | 0.9286 | 13 |
| `premium_subscription` | 0.8929 | 30 |
| `playback_error` | 0.8916 | 38 |
| `playlist_library` | 0.8846 | 26 |
| `app_crash_bug` | 0.8000 | 8 |
| `content_unavailable` | 0.8000 | 11 |

---

## 8. Retrieval Ablation

> **Note:** Recall@K and MRR are **not reported** because no ground-truth relevance labels
> exist for the retrieval corpus. Coverage (score > 0.15) and platform match rate are used
> as proxy quality signals only.

| Method | Coverage > 0.15 | Avg Top-1 Score | Platform Match Rate |
|---|---|---|---|
| Jaccard baseline (token overlap) | 53.0% | 0.1761 | **58.14%** |
| Hybrid (70% TF-IDF + 20% Jaccard + 10% platform) | **57.0%** | **0.1782** | 48.84% |

**Interpretation:** Hybrid retrieval improves overall coverage (+4pp) and average similarity.
The lower platform match rate for hybrid (48.8% vs 58.1%) reflects a known tradeoff:
the TF-IDF component occasionally reranks semantically strong but platform-mismatched
results above platform-matched ones when semantic similarity dominates. This is an honest
finding — the hybrid is not strictly better on every dimension.

**Current constraint:** The retrieval corpus evaluated here is a 500-example sample.
The full corpus of 34,721 pairs is indexed but was not used in this evaluation due to
build time constraints. This is the primary driver of the 43% rate of examples with
similarity below 0.15.

---

## 9. Escalation Behaviour

Escalation is governed by three independent rules:

1. **Hard risk signals** (billing dispute keywords, hack/compromise language, legal threats) → always ESCALATE
2. **Low classifier confidence** (< 0.40) with high-risk intent → ESCALATE
3. **Insufficient retrieval evidence** (best similarity < 0.12) → ESCALATE

| Metric | Value |
|---|---|
| True escalations in golden set | 30 |
| Predicted escalations | 84 |
| Escalation precision | 32.14% |
| Escalation recall | **90.00%** |
| Escalation F1 | 47.37% |
| False auto-handle rate | **3/30 = 10%** |
| Current threshold (not calibrated) | 0.40 |

**Design rationale:** The policy is intentionally conservative — it prefers over-escalation
(high recall) over missing a billing dispute or security issue (high precision). A missed
escalation on a billing dispute carries higher real-world cost than an unnecessary
routing to a human agent.

The low precision (32%) means 62 of 170 AUTO_HANDLE cases were escalated unnecessarily.
This is primarily driven by the retrieval threshold: when no close historical match is found,
the system escalates rather than generate a potentially irrelevant response. Fixing the
retrieval corpus size (Failure Mode 4) would reduce this significantly.

---

## 10. Example Agent Outputs

**Example 1 — AUTO_HANDLE (playback, Android)**

> Customer: *"Spotify keeps stopping whenever I try to play music on my Android phone."*

```json
{
  "intent": "playback_error",
  "confidence": 0.97,
  "platform": "android",
  "decision": "AUTO_HANDLE",
  "reason": "Intent clear, evidence sufficient, no risk signals",
  "response": "Thanks for the info. What Android and Spotify versions are you currently using? Does this happen on both WiFi and 4G? /SC"
}
```

**Example 2 — ESCALATE (billing dispute)**

> Customer: *"I was charged twice for premium this month. This is unacceptable — I need a refund."*

```json
{
  "intent": "billing_charge",
  "confidence": 0.95,
  "platform": "unknown",
  "decision": "ESCALATE",
  "reason": "High-risk signal(s) detected: billing_dispute",
  "response": "We understand this is urgent. Please DM us with your account details and a billing specialist will assist you immediately. /SC"
}
```

**Example 3 — LOW CONFIDENCE → ESCALATE**

> Customer: *"nothing works please just help me"*

```json
{
  "intent": "billing_charge",
  "confidence": 0.16,
  "platform": "unknown",
  "decision": "ESCALATE",
  "reason": "Intent confidence 0.16 below hard threshold 0.40"
}
```

---

## 11. Top Failure Modes

Full analysis with real examples in `docs/failure_analysis.md`. Summary:

| # | Failure Mode | Scale | Root Cause |
|---|---|---|---|
| 1 | Intent misclassification at category boundaries | 43/200 (21.5%) | TF-IDF classifier ambiguous at intent boundaries with shared vocabulary |
| 2 | Missed escalation (false auto-handle) | 3/30 (10%) | Escalation keywords too narrow; soft billing signals not captured |
| 3 | Over-escalation (false escalate) | 62/170 (36%) | Retrieval threshold fires on low-coverage niche queries |
| 4 | Retrieval coverage collapse | 86/200 (43%) | 500-example corpus too small; Jaccard fails on paraphrase variation |
| 5 | Template fallback as majority path | 107/200 (53.5%) | No LLM API key; retrieval corpus too small for evidence-based fallback |

---

## 12. What is Misleading About My Headline Number?

**Headline: Intent Accuracy = 90.50%, Macro F1 = 89.25%**

This number should be treated as provisional, not as production-level accuracy.
Four specific reasons:

**1. Golden-set labels are not human-verified.**
All 200 intent labels in the golden set are `label_source = "kiro_proposed"` with
`human_verified = false`. They were generated by a two-stage process: first a
keyword/regex priority system, then a semantic second-pass by an AI assistant.
No human annotator independently verified all 200 labels before evaluation.

The classifier was trained on the *same keyword-priority logic* used to generate labels.
At intent boundaries — where two intents share vocabulary — the classifier will reproduce
the keyword system's decision and score correctly, not because it understood the message
semantically, but because it reproduced the same heuristic. This creates optimistic bias
at the boundary between `device_platform` / `playback_error` and
`premium_subscription` / `billing_charge`.

**2. The taxonomy itself was initially built from keywords.**
The 9-intent taxonomy was derived from keyword frequency analysis on training data.
When the evaluation labels are produced by the same keyword logic used to create the taxonomy,
the classifier is partially evaluated against its own training signal. A human-labelled
golden set using the taxonomy *definition* rather than its keyword keywords would
likely reveal additional confusions.

**3. Retrieval has no ground-truth relevance labels.**
Coverage (score > 0.15) is a proxy signal, not a true precision/recall measure.
There are no human-judged relevant/irrelevant labels for retrieved pairs.
The reported retrieval improvement from Jaccard (53%) to Hybrid (57%) is directionally
meaningful but cannot be verified as a genuine precision improvement.

**4. Response quality was not evaluated.**
All 200 responses used deterministic templates — no LLM generation and no LLM judge
was available. The 90.5% intent accuracy says nothing about whether the responses
are helpful, grounded, accurate, or appropriate.

---

## 13. Known Limitations

| Limitation | Impact |
|---|---|
| Golden set not fully human-labelled | Headline metrics may overstate real performance |
| Retrieval corpus limited to 500-example sample | 43% of queries find no useful evidence; most responses are templates |
| No LLM API key during evaluation | Response quality dimension entirely unmeasured |
| LLM-as-judge not run | Cannot report judge scores or human-agreement kappa |
| Dataset is 2013–2017 | Spotify features, pricing, and policies have changed; old resolutions may be incorrect |
| Escalation labels are rule-derived | Escalation evaluation reflects heuristic quality, not human judgment |
| Platform detection accuracy: 69.77% on 43 labelled examples | Small sample; platform labels derived from regex |

---

## 14. Engineering Decision Log

10 non-obvious decisions made during implementation:

| # | Decision | Why | Alternative considered | Why not |
|---|---|---|---|---|
| 1 | Temporal split (not random) | Prevents leakage; simulates real deployment | Random 80/20 split | Near-duplicate conversations in both splits inflate metrics |
| 2 | Drop DM-only responses from retrieval corpus | "Please DM us" with no content is useless evidence; 5.2% dropped | Keep all responses | 30% of responses are DM redirects; retrieval returns them as top evidence |
| 3 | Platform-aware retrieval boost | iOS and Android resolutions are materially different | Flat semantic retrieval | Mismatched platform evidence produces wrong instructions |
| 4 | Hybrid retrieval (TF-IDF + Jaccard + platform) | Captures exact token match, semantic proximity, and device context | Dense embeddings (sentence-transformers) | Build time constraint; 34k pairs take ~4 min to embed on CPU |
| 5 | TF-IDF + LR classifier (no fine-tuned BERT) | Fast, reproducible, interpretable; competitive on 9 clean intents | Fine-tuned DistilBERT | Requires GPU, longer training, marginal gain on small-taxonomy task |
| 6 | 9 intents — not fewer | billing_charge and premium_subscription have different escalation policies; collapsing them loses the signal | 5–6 broader intents | Loses billing-dispute escalation trigger |
| 7 | Escalation prioritises recall over precision | Missing a billing dispute is costlier than unnecessary escalation | Balanced F1 threshold | False negative on a real dispute has higher real-world cost |
| 8 | Confidence threshold 0.40 (not calibrated on val) | Initial value; intended to be swept on validation data | Calibrated threshold | Time constraint; calibration script exists but not run |
| 9 | Template fallback when no LLM API key | Ensures reproducibility without API dependency; reviewer can run without credentials | Fail hard if no key | Breaks the <15-minute reproduction requirement |
| 10 | Keyword-derived golden set labels | Practical for one-day timeline; fully documented | Human annotation | Requires 2–3 hours of annotation work; out of scope for submission timeline |
| 11 | Two-level taxonomy (keyword priority → semantic repass) | Reduces labelling errors at boundaries compared to pure keyword rules | Single-pass keyword only | Single-pass misclassifies multi-keyword messages |
| 12 | Leakage verification by conversation ID | Confirms no golden example appears in retrieval corpus | No check | Temporal split is necessary but not sufficient guarantee |

---

## 15. One More Week

Ordered by expected impact on the system's weakest points:

1. **Human annotation of 33 highest-priority label disagreements** (2–3 hours).
   The 24 intent conflicts and 9 escalation conflicts between rule labels and Kiro labels
   are the cheapest, highest-value investment. This directly validates or refutes
   the 90.5% headline number.

2. **Full 34,721-pair retrieval corpus with dense embeddings.**
   `build_index.py` already exists and is tested. Running it on the full corpus eliminates
   the primary driver of Failure Modes 4 and 5 (86 low-coverage examples, 107 template
   fallbacks). Expected: coverage above 0.15 increases from 57% to ~80%.

3. **LLM-grounded generation + LLM-as-judge evaluation.**
   `generator.py` and `evaluate.py` already support `gpt-4o-mini` via `OPENAI_API_KEY`.
   Setting the key and running `python evaluate.py` produces LLM judge scores across
   7 dimensions (relevance, correctness, groundedness, actionability, tone, escalation,
   no-hallucination). This is the only way to measure the response-quality dimension.

4. **Calibrate escalation thresholds per-intent on validation split.**
   The current 0.40 threshold is a starting point. A one-hour parameter sweep on
   `val.jsonl` would reduce the 62 false-escalation cases (36% false-positive rate among
   AUTO_HANDLE examples) while keeping false auto-handle rate at or below 10%.

5. **Conflict-resolution layer for top-2 intent ties.**
   When classifier top-2 probabilities are within 0.05, add a secondary binary
   classifier trained on the most-confused pairs: `device_platform` / `playback_error`,
   `premium_subscription` / `billing_charge`. This addresses the 43 misclassifications
   that concentrate at these boundaries.

---

## 16. Reproduction Instructions

All steps run in under 15 minutes after dependencies and dataset are in place.

### Prerequisites

```bash
cd spotify_agent
pip install -r requirements.txt
cp .env.example .env
# Optional: add OPENAI_API_KEY to .env for LLM generation and judge
```

Place `twcs.csv` at: `../twcs/twcs.csv`

### Individual steps

```bash
python preprocess.py          # ~95s  — reconstruct conversations, split
python build_index.py         # ~4min — build hybrid retrieval index (full corpus)
python build_golden.py        # ~10s  — sample 200-example golden set
python evaluate.py --no-llm   # ~3min — run all baselines on golden set
python failure_analysis.py    # ~15s  — identify failure modes
```

### Single-command run

```bash
python run_all.py             # runs all steps in order, ~10-15 min
python run_all.py --no-llm    # skip LLM judge (no API key needed)
```

### Demo (interactive)

```bash
python run.py --batch         # demo on preset test messages
python run.py                 # interactive CLI
```

### Current evaluation results are already saved

If you only want to inspect results without rerunning:

```
results/full_evaluation.json       # all metrics
results/full_evaluation.md         # formatted report
results/final_predictions.jsonl    # per-example predictions
docs/failure_analysis.md           # failure mode analysis
```

> **⚠ Limitation:** The current evaluation used a 500-example retrieval corpus sample,
> not the full 34,721 pairs. To reproduce with the full corpus, run `python build_index.py`
> before `python evaluate.py`. This takes ~4 minutes on CPU.

---

## 17. Project Structure

```
spotify_agent/
├── config.py                    # all configuration and constants
├── preprocess.py                # data pipeline: reconstruct, split, DM filter
├── build_index.py               # build hybrid retrieval index (ChromaDB)
├── build_golden.py              # sample 200-example golden set from test split
├── quick_intents.py             # derive intent taxonomy from training data
├── intent_classifier.py         # TF-IDF + LR classifier
├── retriever.py                 # Jaccard baseline retriever
├── retrieval/
│   ├── hybrid_retriever.py      # hybrid TF-IDF + Jaccard + platform
│   └── compare_retrieval.py     # ablation: Jaccard vs hybrid
├── agent.py                     # full pipeline: classifier + retrieval + escalation
├── evaluate.py                  # evaluation harness: all baselines + metrics
├── failure_analysis.py          # failure mode identification
├── run.py                       # CLI demo
├── run_all.py                   # one-command full pipeline
├── api.py                       # FastAPI wrapper (GET /health, POST /predict)
├── annotate.py                  # Streamlit annotation tool for golden set
├── requirements.txt
├── .env.example
│
├── data/processed/
│   ├── train.jsonl              # 28,594 training pairs
│   ├── val.jsonl                # 6,127 validation pairs
│   ├── test.jsonl               # 6,128 test pairs
│   ├── retrieval_corpus.jsonl   # 34,721 retrieval pairs (train+val)
│   └── stats.json
│
├── golden_set/
│   ├── golden_set.jsonl         # 200 examples (keyword/rule labels)
│   ├── final_golden_set.csv     # 200 examples (kiro_proposed labels)
│   ├── human_review.csv         # annotation queue (human labels blank)
│   ├── kiro_proposed_labels.csv # semantic second-pass proposals
│   ├── human_review_queue.csv   # 147 examples flagged for review
│   ├── labeling_methodology.md  # full labelling methodology
│   └── review_summary.md
│
├── models/
│   ├── tfidf_vec.pkl            # trained TF-IDF vectoriser
│   └── lr_clf.pkl               # trained LR classifier
│
├── results/
│   ├── full_evaluation.json     # all metrics
│   ├── full_evaluation.md       # formatted evaluation report
│   ├── final_predictions.jsonl  # per-example predictions
│   ├── simple_classifier.json   # TF-IDF+LR standalone results
│   └── trivial_baseline.json    # majority classifier results
│
├── docs/
│   ├── intent_taxonomy.json
│   ├── intent_taxonomy.md
│   ├── failure_analysis.md      # top 5 failure modes with real examples
│   ├── engineering_decisions.md
│   ├── misleading_headline.md
│   └── one_more_week.md
│
└── retrieval/
    └── chroma_db/               # persisted vector index
```

---

*Hiver SDE Intern Take-Home Assignment — SpotifyCares AI Support Agent*
