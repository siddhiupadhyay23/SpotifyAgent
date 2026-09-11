# Human Review Queue — Summary

**Source:** `kiro_proposed_labels.csv`  
**Queue:** `human_review_queue.csv`  
**Total in queue:** 147 of 200 examples (flagged `needs_human_review = true`)

---

## Review reason counts

| Reason | Count |
|---|---|
| Other Uncertainty | 90 |
| Intent Disagrees With Auto | 24 |
| Multiple Competing Intents | 15 |
| Escalation Disagrees With Auto | 9 |
| Short Or Low Context | 9 |
| **Total** | **147** |

---

## Priority explanation

| Priority | Reason | Why important |
|---|---|---|
| 1 | intent_and_escalation_disagree | Both labels conflict between auto and Kiro — highest uncertainty |
| 2 | intent_disagrees_with_auto | Intent differs; escalation agrees — verify correct intent |
| 3 | escalation_disagrees_with_auto | Intent agrees; escalation differs — verify correct decision |
| 4 | multiple_competing_intents | Message matched 3+ intent patterns — pick dominant one |
| 5 | short_or_low_context | Message too short to classify reliably |
| 6 | other_uncertainty | Multi-issue language or other ambiguity signal |

---

## Instructions for reviewer

Open `human_review_queue.csv` in a spreadsheet.

For each row, fill:

- **`human_intent`** — one of the 9 exact intent strings (see `labeling_methodology.md`)
- **`human_escalation`** — `AUTO_HANDLE` or `ESCALATE`
- **`reviewed`** — set to `yes` when done

Work top-down (priority 1 first, then 2, etc.).

Use `original_intent` and `kiro_intent` as reference only — make your own judgment.

When done, merge back into `golden_set.jsonl` using the `example_id` field.

---

## Remaining 53 examples (not in queue)

The 53 examples where `needs_human_review = false` have consistent, high-confidence
labels from both the auto-rule system and Kiro. They can be accepted as-is unless
spot-check reveals errors.
