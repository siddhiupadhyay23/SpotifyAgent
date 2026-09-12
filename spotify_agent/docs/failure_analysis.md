# Failure Analysis — SpotifyCares Support Agent

All examples are taken directly from `results/final_predictions.jsonl` and
`golden_set/final_golden_set.csv`. No examples or metrics are invented.
Evaluation reflects the finalized 200-example human-reviewed and human-labelled golden set.

---

## Top 5 Failure Modes

---

### 1. Intent misclassification against human ground truth (90 / 200 = 45.0%)

**Customer message (g0004):**
> "@115888 it's almost 2018. When will you 'allow' an Apple Watch app? Its like you WANT us to quit and go to Apple Music"

| | Value |
|---|---|
| Human intent | `device_platform` |
| Predicted intent | `playback_error` |
| Confidence | 0.57 |
| Escalation | AUTO_HANDLE (correct) |

**Generated reply:** *"Hi! Check out the official idea and add your vote to let our devs know it's something you'd like to see."*

**Hypothesis:** The TF-IDF+LR classifier achieved 90.5% (0.9050) accuracy, 89.25% macro F1, and 90.44% weighted F1 during initial development when evaluated against rule-derived labels. However, against the 200-example human-reviewed golden set, accuracy is **55.0% (0.5500), macro F1 is 51.28%, and weighted F1 is 56.23% (90 misclassifications out of 200)**. 
"Apple Watch" and "Apple Music" contain music-service terms that share vocabulary with playback errors. At low confidence (0.57), the classifier falls to the most frequent training class (`playback_error`) rather than the correct one (`device_platform`). More broadly, the classifier learned lexical keyword proxies during training; when customers use natural conversational phrasing without explicit target keywords, the classifier fails to discern the underlying semantic intent.

---

### 2. Missed escalation — false AUTO_HANDLE (19 false auto-handles out of 50 true escalations = 38%)

**Customer message (g0019):**
> "@117153 Hi there. I'm being charged for Premium Spotify, but my account is not showing anything so I can't cancel. I tried many times."

| | Value |
|---|---|
| Human escalation | `ESCALATE` |
| Predicted escalation | `AUTO_HANDLE` |
| Intent (correct) | `billing_charge` |
| Confidence | 0.79 |
| Top retrieval sim | 0.17 |

**Agent reasoning:** *"Intent clear, evidence sufficient, no risk signals."*

**Hypothesis:** Human review identified **50 true escalations** in the golden set (compared to 30 true escalations identified by the initial keyword heuristic). The agent produced **19 false auto-handles** (missing 19 out of 50 escalations), resulting in a **38% false auto-handle rate (38.0%) and 62% recall (62.0%)**.
This contrasts sharply with the development heuristic evaluation, which claimed 90% recall and a 10% false auto-handle rate based on only 3 false auto-handles among 30 true escalations.
The escalation rules require explicit dispute keywords (`chargeback`, `unauthorized`, `refund`, `hack`, `stolen`). "Being charged but account shows nothing so I can't cancel" is an active billing dispute requiring internal account lookup, but the customer's phrasing contains none of the rigid trigger keywords. High classifier confidence (0.79) further suppressed escalation. The rule-based escalation system is keyword-sensitive but blind to conversational, implicit risk signals.

---

### 3. Over-escalation — false ESCALATE (53 / 150 AUTO_HANDLE cases = 35.3%)

**Customer message (g0001):**
> "@116380 can you please add General Public, most especially their song Tenderness, to SpotifyAU? My 80s mix isn't complete"

| | Value |
|---|---|
| Human escalation | `AUTO_HANDLE` |
| Predicted escalation | `ESCALATE` |
| Predicted intent | `playback_error` (misclassified; human intent: `content_unavailable`) |
| Top retrieval sim | 0.119 |

**Agent reasoning:** *"Best retrieval score 0.119 below minimum 0.12."*

**Generated reply:** *"Hi! Try restarting Spotify and checking your connection."* — irrelevant to a content-addition request.

**Hypothesis:** The escalation policy escalates whenever retrieval similarity drops below 0.12. With only 500 examples in the evaluated retrieval sample, niche or specific requests (regional content requests, long-tail device queries) return low similarity scores, crossing the threshold mechanically. The policy cannot distinguish "no evidence found because the query is risky" from "no evidence found because the query is unusual and low-stakes." Out of 150 true AUTO_HANDLE cases, 53 were escalated this way — a 35.3% false escalation rate (precision = 36.90%).

---

### 4. Retrieval coverage collapse on 500-example corpus (86 / 200 = 43.0% with sim < 0.15)

**Customer message (g0002):**
> "@SpotifyCares I just wanna how may i do to add a buttom or link to my playlist. So, I attach a screenshot"

| | Value |
|---|---|
| Human intent | `playlist_library` |
| Predicted intent | `playlist_library` (correct) |
| Top retrieval sim | < 0.15 |
| Generation mode | `template_fallback:intent` |

**Generated reply:** *"Hi! Try logging out and back in to resync your library."* — does not address the question.

**Hypothesis:** Jaccard and TF-IDF token-overlap retrieval on a 500-example sample cannot find close matches for queries phrased in non-standard or colloquial ways. 43.0% of all golden examples received no evidence above the 0.15 threshold and fell back to a generic intent template, making the response identical for every message of the same intent regardless of what the customer actually asked. The full retrieval corpus contains 34,721 pairs; using only a 500-example sample during runtime evaluation is the primary driver of this failure.

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

**Hypothesis:** No `OPENAI_API_KEY` was available during evaluation, so LLM generation was never invoked. Combined with the low retrieval coverage in failure mode 4, the system produced generic responses for more than half of all queries. The `template_fallback:intent` path produces the same 9 fixed responses regardless of customer phrasing. This is effectively a lookup table, not a retrieval-augmented system.

---

## What is misleading about my headline number?

During development, the headline result was reported as **90.5% intent accuracy (90.50%), 89.25% macro F1, and 90.44% weighted F1**.

However, on the 200-example human-reviewed golden set, the intent classifier reaches **55.0% accuracy (0.5500), 51.28% macro F1, and 56.23% weighted F1**.

The 90.5% figure is misleading if presented without qualification for the following fundamental methodological reasons:

1. **Taxonomy and silver training data were derived from keyword/rule patterns:** The 9 intent classes were created using regex keyword matching.
2. **Training labels were generated from those rules:** 40,849 training pairs were automatically annotated using the same regex rules.
3. **Initial golden labels were also rule-derived:** The initial 200 golden examples were labeled by the same keyword rules.
4. **Human review subsequently exposed substantial disagreement:** When all 200 examples were subjected to rigorous independent human review, real customer intents diverged sharply from the heuristic labels.
5. **Evaluation circularity:** The 90.5% accuracy simply measured how well a linear TF-IDF classifier could approximate the deterministic regex labeling rules. It did not reflect actual natural language understanding.
6. **Human-grounded evaluation is the primary result:** The **55.0% accuracy on the 200-example human-reviewed golden set** is the true benchmark of intent classification performance.

The gap between **90.5% rule-derived accuracy** and **55.0% human-reviewed accuracy** is a central methodology finding of this project. It illustrates why automated rule-based evaluation creates a false sense of security in customer support AI.

Furthermore:
- **Escalation safety was overstated:** Heuristic labels reported 30 true escalations, 3 false auto-handles, 90% recall, and a 10% false auto-handle rate. Human evaluation reveals that the agent faces **50 true escalations and produces 19 false auto-handles (38% false auto-handle rate, 62% recall)**.
- **Retrieval coverage is a proxy, not Recall@K:** Coverage (>0.15) measures token overlap on a 500-example sample. Without human relevance annotations, Recall@K and MRR cannot be reported.
- **Leakage check limitations:** Leakage verification between the golden set and retrieval corpus verified 0 overlapping agent tweet IDs. While temporal splitting limits overlap, this tweet-level check is not a full conversation-tree leakage guarantee.
- **Offline vector index:** ChromaDB and dense embeddings were indexed offline (`build_index.py`), but the evaluated system relies on lightweight lexical retrieval.
- **Uncalibrated thresholds:** The 0.40 confidence threshold was an initial heuristic; a calibrated threshold sweep on validation data is required to optimize the escalation tradeoff.
- **Response quality was unmeasured (LLM-as-Judge limitation):** Because no `OPENAI_API_KEY` was available in the evaluation environment, 0 LLM judge calls were executed and 0 human reply-quality ratings were completed on the 60 deterministic sample examples. Rubric dimensions (groundedness, relevance, helpfulness, overall quality) and judge-human agreement were not calculated, and no judge metrics are claimed.

---

## One more week

**1. Train on human-labelled data rather than heuristic rules.**
The 200-example human review exposed that the classifier learned keyword proxies rather than semantic intent. Curating human-labelled and human-reviewed training data is the highest-leverage investment to close the gap from 55.0% toward production-grade accuracy.

**2. Full 34,721-pair retrieval corpus integration.**
Scale the evaluated retriever from the 500-example sample to the complete corpus of 34,721 historical pairs. While an offline vector index was built in ChromaDB, integrating the full corpus directly into the evaluated pipeline will eliminate Failure Modes 4 and 5 (86 low-coverage examples and 107 generic template fallbacks).

**3. Calibrate escalation thresholds per-intent on validation data.**
The current single 0.40 confidence and 0.12 retrieval thresholds are uncalibrated heuristics. A parameter sweep on `val.jsonl` will yield a calibrated threshold that reduces the 38% false auto-handle rate while taming the 53 unnecessary escalations.

**4. LLM-grounded generation and judge evaluation.**
Wire in an API key to evaluate grounded response generation and run structured evaluation across relevance, groundedness, and actionability.

**5. Conflict-resolution layer for top-2 intent ties.**
When classifier top-2 probabilities are within 0.05, add a secondary discriminator trained on the most-confused pairs (`device_platform` vs `playback_error`, `premium_subscription` vs `billing_charge`, `app_crash_bug` vs `offline_download`).
