# Failure Analysis — SpotifyCares Support Agent

All examples are taken directly from `results/final_predictions.jsonl` and
`golden_set/final_golden_set.csv`. No examples or metrics are invented.
Counts are from `results/full_evaluation.json`.

---

## Top 5 Failure Modes

---

### 1. Intent misclassification at category boundaries (43 / 200 = 21.5%)

**Customer message (g0004):**
> "@115888 it's almost 2018. When will you 'allow' an Apple Watch app? Its like you WANT us to quit and go to Apple Music"

| | Value |
|---|---|
| Expected intent | `device_platform` |
| Predicted intent | `playback_error` |
| Confidence | 0.57 |
| Escalation | AUTO_HANDLE (correct) |

**Generated reply:** *"Hi! Check out the official idea and add your vote to let our devs know it's something you'd like to see."*

**Hypothesis:** The TF-IDF+LR classifier was trained on keyword-derived labels.
"Apple Watch" and "Apple Music" contain music-service terms that share vocabulary with
playback errors. At low confidence (0.57), the classifier falls to the most frequent
training class (`playback_error`, 38 examples) rather than the correct one
(`device_platform`, 33 examples). Both intents are close in training frequency and
have overlapping surface vocabulary. A semantic discriminator trained on human-labelled
boundary cases would separate them.

---

### 2. Missed escalation — false AUTO_HANDLE (3 / 30 true escalations = 10%)

**Customer message (g0019):**
> "@117153 Hi there. I'm being charged for Premium Spotify, but my account is not showing anything so I can't cancel. I tried many times."

| | Value |
|---|---|
| Expected escalation | `ESCALATE` |
| Predicted escalation | `AUTO_HANDLE` |
| Intent (correct) | `billing_charge` |
| Confidence | 0.79 |
| Top retrieval sim | 0.17 |

**Agent reasoning:** *"Intent clear, evidence sufficient, no risk signals."*

**Hypothesis:** The escalation rules require explicit dispute keywords (`chargeback`,
`unauthorized`, `refund`). "Being charged but account shows nothing" is semantically
a billing dispute requiring account access, but the surface phrasing contains none of
the trigger keywords. High classifier confidence (0.79) further suppressed escalation.
The rule system is keyword-sensitive but not semantically aware of billing-risk context.

---

### 3. Over-escalation — false ESCALATE (62 / 170 AUTO_HANDLE cases = 36%)

**Customer message (g0001):**
> "@116380 can you please add General Public, most especially their song Tenderness, to SpotifyAU? My 80s mix isn't complete"

| | Value |
|---|---|
| Expected escalation | `AUTO_HANDLE` |
| Predicted escalation | `ESCALATE` |
| Intent | `playback_error` (misclassified; actual: content request) |
| Top retrieval sim | 0.119 |

**Agent reasoning:** *"Best retrieval score 0.119 below minimum 0.12."*

**Generated reply:** *"Hi! Try restarting Spotify and checking your connection."* — irrelevant to a content-addition request.

**Hypothesis:** The escalation policy escalates whenever retrieval similarity drops below
0.12. With only 500 examples in the retrieval corpus, niche or specific requests (regional
content additions, long-tail device issues) return no close match, crossing the threshold
mechanically. The policy cannot distinguish "no evidence found because the query is risky"
from "no evidence found because the query is unusual and low-stakes." 62 AUTO_HANDLE
cases were escalated this way — a 36% false-positive rate among non-escalation cases.

---

### 4. Retrieval coverage collapse on 500-example corpus (86 / 200 = 43% with sim < 0.15)

**Customer message (g0002):**
> "@SpotifyCares I just wanna how may i do to add a buttom or link to my playlist. So, I attach a screenshot"

| | Value |
|---|---|
| Expected intent | `playlist_library` |
| Predicted intent | `playlist_library` (correct) |
| Top retrieval sim | < 0.15 |
| Generation mode | `template_fallback:intent` |

**Generated reply:** *"Hi! Try logging out and back in to resync your library."* — does not address the question.

**Hypothesis:** Jaccard token-overlap retrieval on a 500-example sample cannot find
close matches for queries phrased in unusual or non-standard ways. 43% of all golden
examples received no evidence above the 0.15 threshold and fell back to a generic
intent template, making the response identical for every message of the same intent
regardless of what the customer actually asked. The full retrieval corpus contains
34,721 pairs; using only 500 is the primary driver of this failure.

---

### 5. Template fallback as the majority generation path (107 / 200 = 53.5%)

**Customer message (g0002, same as above):**
> "@SpotifyCares I just wanna how may i do to add a buttom or link to my playlist."

| | Value |
|---|---|
| Generation mode | `template_fallback:intent` |
| Evidence used | None |
| Response | Generic `playlist_library` template |

**Scale of the problem:**

| Mode | Count | % |
|---|---|---|
| `template_fallback:intent` | 107 | 53.5% |
| `template_fallback:top_evidence` | 73 | 36.5% |
| `escalation_override` | 20 | 10.0% |
| LLM generation | 0 | 0% |

**Hypothesis:** No `OPENAI_API_KEY` was available during evaluation, so LLM generation
was never invoked. Combined with the low retrieval coverage in failure mode 4, the system
produced generic responses for more than half of all queries. The `template_fallback:intent`
path produces the same 9 fixed responses regardless of customer phrasing. This is
effectively a lookup table, not a retrieval-augmented system. The architecture is correct
but the two prerequisites for meaningful generation — a large retrieval corpus and a
generation model — were both absent during this evaluation run.

---

## What is misleading about my headline number?

The headline result is **Intent Macro F1 = 0.8925** on the 200-example golden set.

This number is likely optimistic for at least three reasons.

**The golden-set labels were not human-labelled.** Every intent label in the golden set
was generated by a keyword/regex priority rule, then re-examined semantically by the
Kiro AI assistant. No human annotator reviewed all 200 examples before evaluation.
The classifier was trained on labels produced by the same keyword logic used to evaluate
it. When a message is borderline between two intents, the label assigned during data
preparation reflects which keyword fired first in the priority order — not which intent
a human support agent would choose. The classifier will score correctly on those examples
not because it understood the query but because it reproduced the same keyword-priority
decision the labelling system made. This inflates measured F1.

**The evaluation split does not reflect real deployment distribution.** The golden set
is drawn from a 9-day window (25 Nov–3 Dec 2017). Seasonal and event-driven conversation
patterns in this window may not represent the full year. Rarer intents like `app_crash_bug`
(n=8) and `content_unavailable` (n=11) have so few golden examples that their per-intent
F1 estimates have high variance (±0.2 at n=8 is a reasonable 95% confidence interval).

**Response quality was not measured.** The Macro F1 describes only intent classification.
It says nothing about whether the drafted replies are helpful, grounded, or accurate.
Because LLM generation was unavailable, all 200 responses used deterministic templates.
The "support agent" dimension of the system — the part that actually matters to a
customer — was never evaluated.

---

## One more week

**1. Human annotation of the 33 highest-priority label disagreements.**
The 24 examples where Kiro's semantic label disagrees with the keyword auto-label, and
the 9 escalation disagreements, are the cheapest and highest-value investment. Two to
three hours of manual review would establish whether current evaluation failures are model
errors or label errors, and would allow recalculation of all metrics with reliable ground truth.

**2. Full 34,721-pair retrieval corpus with dense embeddings.**
Replace the 500-example Jaccard retriever with `sentence-transformers/all-MiniLM-L6-v2`
indexed over the complete corpus. The infrastructure (`retriever.py`, `build_index.py`)
is already written and tested; this requires only running `build_index.py` on the full
corpus. Expected impact: retrieval coverage above 0.15 from 57% to ~80%, cutting failure
modes 4 and 5 in half.

**3. LLM-grounded generation and judge evaluation.**
Wire in `gpt-4o-mini` using the grounding prompt already in `generator.py`. Run the
5-dimension LLM judge rubric (`evaluate.py --llm`) on 60 sampled examples. This is the
only way to measure groundedness, actionability, and hallucination rate — the dimensions
that make RAG systems valuable and that are entirely unmeasured in the current results.

**4. Calibrate escalation thresholds per-intent on the validation split.**
The current policy applies a single 0.40 confidence threshold and a single 0.12 retrieval
threshold to all intents. A two-hour sweep on `val.jsonl` (6,127 examples) would find
the threshold pair that minimises false-auto-handle rate while keeping the false-ESCALATE
rate below 20%. This directly addresses failure mode 3 (62 over-escalations).

**5. Add a conflict-resolution layer for top-2 intent ties.**
When the classifier's top-2 predicted intents are within 0.05 probability of each other,
run a secondary binary classifier trained specifically on the most common confusion pairs
(`device_platform` vs `playback_error`, `premium_subscription` vs `billing_charge`,
`app_crash_bug` vs `offline_download`). This addresses failure mode 1 at the boundary
cases where single-model confidence is lowest.
