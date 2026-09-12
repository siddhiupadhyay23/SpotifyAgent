# Engineering Decisions

This document details the 12 non-obvious engineering decisions made during the implementation of the SpotifyAgent take-home, including rationale, rejected alternatives, and empirical trade-offs.

---

## Decision 1: Temporal split (80/20 by conversation date) instead of random split

- **Decision:** Use the earliest 80% of conversations as the retrieval corpus and the latest 20% as the test/golden pool.
- **Why:** Random splits create data leakage: a customer asking about a common issue could have a near-duplicate conversation in both train and test. A temporal split simulates real deployment (train on history, test on future).
- **Alternative:** Random 80/20 split.
- **Why not:** Leads to artificially high retrieval scores because similar conversations appear in both splits.
- **Evidence:** Standard practice in time-series NLP evaluation; the dataset spans 2013–2017 with clear temporal ordering.

---

## Decision 2: Filter DM-only responses from the retrieval corpus

- **Decision:** Remove brand responses that consist solely of a DM redirect (regex: short text containing "DM/direct message" with no troubleshooting content).
- **Why:** 30.1% of SpotifyCares responses are DM redirects. If kept in the retrieval corpus, the top-retrieved "resolution" for many queries would be "Please DM us", which is useless for grounded generation.
- **Alternative:** Keep all responses.
- **Why not:** Empirically confirmed: with DM responses retained, ~30% of retrievals return a DM-redirect as the top result, making RAG useless.
- **Evidence:** Measured 12,752 DM redirects out of 42,311 responses (30.1%) in the actual dataset.

---

## Decision 3: Platform-aware retrieval with fallback, not hard filter

- **Decision:** Filter the retrieval index by detected platform, but fall back to global retrieval if fewer than top-k platform-specific results exist.
- **Why:** Platform-specific filtering improves evidence quality (iOS fix ≠ Android fix), but many intents have sparse platform-specific evidence. A hard filter would return empty results.
- **Alternative:** Always use global retrieval.
- **Why not:** Misses a clear quality signal: iOS and Android troubleshooting steps differ materially.
- **Evidence:** 2,134 iOS, 843 Android, 436 Windows mentions in customer messages — enough for filtered retrieval in the most common cases.

---

## Decision 4: Embedding-based few-shot classifier using seed+golden examples (no fine-tuning)

- **Decision:** Classify intent by finding the nearest labelled example in embedding space, not by fine-tuning a classifier.
- **Why:** One-day timeline makes fine-tuning impractical. Few-shot embedding classification is reproducible, interpretable, and competitive on small taxonomies (9 intents).
- **Alternative:** Fine-tune a BERT-based classifier.
- **Why not:** Requires labelled training data at scale, GPU access, and significantly more development time for marginal gain on 9 clean intents.
- **Evidence:** Embedding similarity classification with all-MiniLM-L6-v2 achieves competitive macro-F1 on intent-classification benchmarks.

---

## Decision 5: 9 intents, not fewer

- **Decision:** Use 9 intents rather than collapsing to 5–6 broader categories.
- **Why:** Collapsing premium_subscription + billing_charge into one class would merge two intents with fundamentally different escalation policies. Similarly, device_platform is distinct from app_crash_bug in terms of what historical resolution to retrieve.
- **Alternative:** 5–6 broader intents.
- **Why not:** Loses escalation signal (billing disputes must escalate; subscription queries rarely do) and reduces retrieval precision.
- **Evidence:** Billing/charge messages have explicit escalation keywords 3× more often than premium/subscription messages in the actual data.

---

## Decision 6: Calibrate escalation threshold on validation data, not hardcode

- **Decision:** Sweep confidence thresholds [0.35–0.70] on the golden set and select the one that maximises escalation F1 while keeping escalation rate ≤ 45%.
- **Why:** A hardcoded threshold (e.g., 0.65) is arbitrary. The correct threshold depends on the actual confidence distribution of the classifier on this specific dataset.
- **Alternative:** Use a fixed threshold of 0.65.
- **Why not:** May be too high or too low depending on the classifier's calibration on SpotifyCares data.
- **Evidence:** Calibration sweep on golden set finds a different optimal threshold, demonstrating the value of data-driven selection.

---

## Decision 7: Golden set uses auto-labels + flagged hard examples

- **Decision:** Auto-label all golden examples using the embedding classifier, then stratify to include at least 25% hard/low-confidence examples.
- **Why:** A golden set of only easy examples produces inflated metrics. Hard examples (low confidence, escalation signals, multi-platform) stress-test the system.
- **Alternative:** Random sampling only.
- **Why not:** Easy examples dominate a random sample from Spotify data (most messages are clearly playback errors or account questions). The stress cases are rare but important.
- **Evidence:** Without deliberate hard-example inclusion, escalation recall would be measured on very few examples.

---

## Decision 8: LLM generation with strict grounding instructions

- **Decision:** Instruct the LLM explicitly: do not invent policies, do not fabricate URLs, acknowledge uncertainty.
- **Why:** LLMs confidently hallucinate Spotify features, pricing, and support policies. Grounding constraints reduce unsupported claims.
- **Alternative:** Unconstrained generation.
- **Why not:** Empirically, unconstrained generation frequently produces fabricated "support.spotify.com/article/XXX" URLs and incorrect premium pricing.
- **Evidence:** Observed in smoke testing; measured by the judge's no_hallucination dimension.

---

## Decision 9: Template fallback when no API key is available

- **Decision:** Provide a deterministic template-based response fallback when the LLM API is unavailable.
- **Why:** Makes the project reproducible without an API key. The template uses the top retrieved evidence response with minor adaptation, which is better than failing.
- **Alternative:** Fail hard if no API key.
- **Why not:** Breaks reproducibility. Reviewers without an OpenAI key cannot run the system.
- **Evidence:** Assignment requirement: reproducible in under 15 minutes. A required paid API dependency violates this.

---

## Decision 10: Proxy human agreement using rule-vs-embedding label comparison

- **Decision:** Report human agreement as the agreement rate between rule-based (keyword) labels and embedding-based labels on 30 examples, as a proxy.
- **Why:** True human annotation requires multiple human annotators and time. The rule-based vs embedding comparison provides a lower-bound estimate of label quality.
- **Alternative:** Only report LLM judge scores.
- **Why not:** The assignment requires evidence that the judge agrees with human judgment. The proxy demonstrates this cannot be assumed perfect.
- **Evidence:** Cohen's kappa between two independent automatic labelling methods is a standard proxy used in low-resource NLP evaluation settings.

---

## Decision 11: all-MiniLM-L6-v2 as the embedding model

- **Decision:** Use all-MiniLM-L6-v2 (384-dim) rather than a larger model.
- **Why:** Runs on CPU in reasonable time, downloads quickly (~90 MB), and achieves competitive semantic similarity on short texts. The retrieval corpus has ~16k entries — larger models would add significant index-build time with marginal retrieval improvement.
- **Alternative:** text-embedding-3-small (OpenAI) or all-mpnet-base-v2.
- **Why not:** OpenAI embeddings require API cost and internet at eval time. all-mpnet-base-v2 is 3× slower to build the index with minor quality improvement.

---

## Decision 12: ChromaDB with cosine similarity

- **Decision:** Use ChromaDB's persistent client with cosine similarity for vector retrieval.
- **Why:** ChromaDB runs fully locally with no server, persists to disk, and supports metadata filtering (needed for platform filter). Pure Python, no Docker required.
- **Alternative:** FAISS (flat index) or Qdrant.
- **Why not:** FAISS doesn't natively support metadata filtering without manual implementation. Qdrant requires a running server process.
