# LLM-as-Judge Evaluation Rubric — Reply Quality

**Version:** 1.0  
**Target Agent:** SpotifyCares Support Agent  
**Evaluation Scope:** Draft response quality evaluated against customer issue, retrieved historical resolutions, and escalation decision.

---

## Evaluation Constraints & Privacy Boundary

1. **Information Isolation:** The judge model evaluates **ONLY**:
   - Customer message
   - Retrieved historical resolution evidence (snippets and similarity scores)
   - Agent draft reply
   - Agent escalation decision (`AUTO_HANDLE` or `ESCALATE`) and escalation reasoning
2. **Ground-Truth Blinding:** The judge **MUST NOT** be provided with the human-annotated ground-truth intent or human escalation labels. This prevents label leakage and evaluates real-world response utility independently.
3. **Deterministic Scoring:** The judge must output structured JSON scoring each dimension from 1 to 5 with a concise technical justification.

---

## Rubric Dimensions

### 1. Groundedness (1–5)
Measures the extent to which the claims, instructions, URLs, and troubleshooting steps in the draft response are anchored in verified historical evidence or official platform behavior, rather than hallucinated.

| Score | Anchor | Definition |
|:---:|:---|:---|
| **5** | Fully Supported | Every factual claim, step, and URL in the response is directly grounded in the retrieved historical evidence. Zero hallucination. |
| **4** | Mostly Supported | The core troubleshooting instructions are grounded; minor generic phrasing or polite conversational filler is added without introducing false claims. |
| **3** | Partially Supported | Some recommendations align with the retrieved evidence, but the response contains unsupported procedural steps or speculative advice. |
| **2** | Substantially Unsupported | Substantial parts of the reply make assertions, steps, or policy claims that have no basis in the retrieved evidence. |
| **1** | Hallucinated / Contradictory | The response is fabricated, invents non-existent features/settings, hallucinates broken URLs, or directly contradicts the evidence. |

---

### 2. Relevance (1–5)
Measures how directly and accurately the response addresses the customer's specific reported issue and platform context.

| Score | Anchor | Definition |
|:---:|:---|:---|
| **5** | Directly Targeted | Directly addresses the user's primary symptom, error, and platform context (e.g. iOS vs Android vs Desktop) without irrelevant tangents. |
| **4** | Mostly Relevant | Addresses the main issue with minor generic troubleshooting that is still applicable to the customer's scenario. |
| **3** | Partially Relevant | Acknowledges the broad problem area (e.g. audio issues), but misses the specific complaint or provides instructions for the wrong platform. |
| **2** | Largely Irrelevant | Responds to tangential keywords rather than the user's core problem (e.g. giving login advice when the customer reported a billing overcharge). |
| **1** | Irrelevant | Completely fails to address the customer's message or provides totally unrelated advice. |

---

### 3. Helpfulness & Actionability (1–5)
Measures whether the response gives the customer clear, actionable next steps, appropriate tone, and safe routing.

| Score | Anchor | Definition |
|:---:|:---|:---|
| **5** | Highly Actionable & Safe | Gives crystal-clear, step-by-step guidance. If escalation is required (e.g. account takeover, billing dispute), provides prompt, secure escalation instructions (e.g. DM request). |
| **4** | Useful with Minor Omissions | Actionable and helpful, but could be clearer (e.g. missing an explicit navigation path or app setting location). |
| **3** | Somewhat Useful | Offers high-level advice (e.g. "try restarting"), but lacks specifics needed to resolve complex technical or account problems. |
| **2** | Limited Usefulness | Gives repetitive, trivial, or circular advice that is unlikely to resolve the issue or causes customer frustration. |
| **1** | Unhelpful / Harmful | Misleading, confusing, or dangerous advice (e.g. telling a customer with an unauthorized charge to wait rather than escalate). |

---

### 4. Overall Quality (1–5)
Holistic assessment balancing accuracy, tone, safety, and brand appropriateness for SpotifyCares.

| Score | Definition |
|:---:|:---|
| **5** | Exemplary support response — accurate, grounded, helpful, empathetic, and safe. Production-ready. |
| **4** | Good response — minor phrasing or formatting adjustments possible, but safe to send to a user. |
| **3** | Borderline — passable generic response, but lacks personalization or complete grounding. |
| **2** | Deficient — noticeably weak response that requires significant human revision before sending. |
| **1** | Unacceptable — wrong, hallucinated, or unsafe response that should never be dispatched. |

---

## Structured Output Schema

The judge returns a strict JSON object:

```json
{
  "groundedness": 1-5,
  "relevance": 1-5,
  "helpfulness": 1-5,
  "overall": 1-5,
  "rationale": "Concise 1-2 sentence justification for the assigned scores."
}
```

---

## Evaluation Status & Submission Limitation Disclosure

- **Deterministic Judge Sample:** Exactly 60 examples sampled deterministically (`seed=42`) from `final_golden_set.jsonl`.
- **Rubric Dimensions:** Groundedness, Relevance, Helpfulness, Overall Quality.
- **LLM Judge Examples Scored:** 0 (evaluation blocked: no `OPENAI_API_KEY` available in the test environment).
- **Human Reply-Quality Ratings:** 0 (review template `golden_set/reply_quality_human_review.csv` contains all 60 rows with score fields left blank for independent human annotation).
- **Judge-Human Agreement:** Not calculated (pending human completion and judge execution; quadratic-weighted Cohen's kappa harness prepared in `spotify_agent/evaluation/llm_judge.py`).
- **No Claimed Judge Metrics:** No synthetic scores or fabricated agreements are claimed.

