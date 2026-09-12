# Human Annotation Guide — Reply Quality Evaluation

**Task:** Evaluate the quality of AI-generated support draft replies on 60 customer queries.  
**Review File:** [`golden_set/reply_quality_human_review.csv`](file:///c:/Users/Siddhi/Desktop/Hiver/spotify_agent/golden_set/reply_quality_human_review.csv)  
**Scale:** Integer ratings from 1 to 5 for each dimension.

---

## Instructions for Human Reviewers

For each row in `reply_quality_human_review.csv`:
1. Read the `customer_message`.
2. Read the `generated_response`.
3. Provide an integer score from 1 to 5 for each of the four dimensions below.
4. Leave optional observations in `human_notes` for difficult or edge cases.
5. Do not consult or populate the model's judge predictions while scoring.

---

## Scoring Dimensions

### 1. Groundedness (`human_groundedness`)
Is the response factually grounded in plausible Spotify procedures without hallucinating features, links, or policies?
- **5 = Fully Grounded:** Every instruction, setting path, and claim is accurate and sound.
- **4 = Mostly Grounded:** Solid core troubleshooting with minor generic filler phrasing.
- **3 = Partially Grounded:** High-level advice is okay, but includes unsupported assumptions.
- **2 = Substantially Unsupported:** Misleading or non-existent steps/features mentioned.
- **1 = Hallucinated:** Pure hallucination, invented URLs, or flatly incorrect product behavior.

### 2. Relevance (`human_relevance`)
Does the response directly address the specific problem and platform stated by the user?
- **5 = Directly Relevant:** Directly answers the customer's problem on the correct platform.
- **4 = Mostly Relevant:** Addresses the core issue with minor generic troubleshooting.
- **3 = Partially Relevant:** On the general topic (e.g. sound issues), but misses the specific complaint.
- **2 = Largely Irrelevant:** Latches onto a minor keyword while missing the main issue.
- **1 = Completely Irrelevant:** Completely unrelated to what the customer asked.

### 3. Helpfulness (`human_helpfulness`)
Does the response give clear, actionable next steps, appropriate tone, and safe escalation?
- **5 = Highly Actionable:** Crystal-clear guidance, safe routing, and appropriate tone.
- **4 = Useful:** Helpful with minor omissions (e.g. doesn't specify exact menu location).
- **3 = Somewhat Useful:** Generic advice (e.g. "reinstall the app") that may not fully solve the issue.
- **2 = Limited Usefulness:** Repetitive or unhelpful stock phrase that frustrates the customer.
- **1 = Unhelpful / Dangerous:** Misleading advice that could cause data loss or security risk.

### 4. Overall Quality (`human_overall`)
Holistic assessment of whether this response is acceptable for customer dispatch:
- **5 = Excellent:** Production ready, polite, accurate, and concise.
- **4 = Good:** Minor phrasing tweaks possible, but safe and effective to send.
- **3 = Borderline:** Passable generic reply, but suboptimal personalization.
- **2 = Deficient:** Poor quality, would require substantial revision by a human agent.
- **1 = Unacceptable:** Wrong, offensive, or hazardous to customer account safety.

---

## Status & Submission Limitation Disclosure

- **Deterministic Judge Sample:** Exactly 60 examples sampled deterministically (`seed=42`) from `final_golden_set.jsonl`.
- **Rubric Dimensions:** Groundedness, Relevance, Helpfulness, Overall Quality.
- **Human Reply-Quality Ratings:** 0 (all score columns in `reply_quality_human_review.csv` remain blank for independent human annotation).
- **LLM Judge Examples Scored:** 0 (execution blocked: no `OPENAI_API_KEY` available in the test environment).
- **Judge-Human Agreement:** Not calculated (pending human completion and judge execution; quadratic-weighted Cohen's kappa harness prepared in `spotify_agent/evaluation/llm_judge.py`).
- **No Claimed Judge Metrics:** No synthetic scores or fabricated agreements are claimed.

