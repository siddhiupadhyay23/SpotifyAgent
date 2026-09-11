# Simple RAG Baseline

**Pipeline:** TF-IDF+LR intent classifier -> Jaccard retrieval (top-3, 500-sample) -> template generation (no API key)

No platform filtering. No risk-aware escalation. Intentionally simple.

## Results (n=200)

| Metric | Score |
|---|---|
| Intent Accuracy | 0.9050 |
| Intent Macro F1 | 0.8925 |
| Intent Weighted F1 | 0.9044 |
| Retrieval Coverage (score>0.15) | 0.4650 |
| Avg Top-1 Similarity | 0.1610 |
| Runtime | 1.8s |

## Generation

**No LLM API key set.** Template fallback used. Set OPENAI_API_KEY and rerun for grounded LLM generation.

## Notes

- Retrieval uses Jaccard token overlap on a 500-example sample.
- No platform-aware filtering (that is the Final System improvement).
- Intent classification is identical to Simple Classifier baseline.
