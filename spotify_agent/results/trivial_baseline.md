# Trivial Baseline — Majority-Class Predictor

**Method:** Predict every incoming message as `playback_error`,
the most frequent intent in the training split (count=2,478).

**Why this is the right trivial baseline:** A majority-class predictor requires
no understanding of the message. Any useful classifier must beat this.

## Results on golden set (n=200)

| Metric | Score |
|---|---|
| Accuracy | 0.1900 |
| Macro F1 | 0.0355 |
| Weighted F1 | 0.0607 |

Macro F1 is the headline metric because the golden set is intentionally
imbalanced (mirroring real support volume). A majority predictor scores
near-zero macro F1 because it gets 0 F1 on every non-majority class.
