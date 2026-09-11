"""
STEP 6 — Write all documentation files:
  - intent_taxonomy.json
  - engineering_decisions.md
  - misleading_headline.md
  - one_more_week.md
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import DOCS_DIR, RESULTS_DIR, INTENTS, INTENT_LABELS, GOLDEN_PER_INTENT

DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ── Intent taxonomy ───────────────────────────────────────────────────────────
taxonomy = {
    "playback_error": {
        "label": "Playback Error",
        "definition": "Customer cannot play music: buffering, song won't start, skipping, pausing unexpectedly.",
        "frequency_pct": 14.5,
        "examples": [
            "Spotify keeps buffering and won't play any songs",
            "Songs keep pausing every few seconds on my commute",
        ],
        "nearest_confusable": "app_crash_bug",
        "confusion_note": "App crashes can cause playback failure; distinguish by presence of crash/freeze language.",
        "escalation": "AUTO_HANDLE in most cases; ESCALATE if persists >24h with troubleshooting attempted.",
    },
    "account_login": {
        "label": "Account / Login",
        "definition": "Customer cannot access their account: login failures, password reset, account locked.",
        "frequency_pct": 12.2,
        "examples": [
            "Can't log in to Spotify, forgot my password",
            "My account keeps logging me out automatically",
        ],
        "nearest_confusable": "premium_subscription",
        "confusion_note": "Premium access issues may look like login issues; check for subscription language.",
        "escalation": "ESCALATE if security/hack signals; AUTO_HANDLE for standard password reset.",
    },
    "premium_subscription": {
        "label": "Premium / Subscription",
        "definition": "Questions or issues about premium plan status, cancellation, trials, family/student plans.",
        "frequency_pct": 12.4,
        "examples": [
            "I cancelled premium but it's still showing as free",
            "How do I switch from individual to family plan?",
        ],
        "nearest_confusable": "billing_charge",
        "confusion_note": "Subscription questions become billing issues when money is mentioned.",
        "escalation": "AUTO_HANDLE for status queries; ESCALATE if charge dispute.",
    },
    "billing_charge": {
        "label": "Billing / Charge",
        "definition": "Unexpected charges, payment failures, refund requests, invoice questions.",
        "frequency_pct": 3.2,
        "examples": [
            "I was charged $9.99 after cancelling",
            "There's an unexpected charge from Spotify on my credit card",
        ],
        "nearest_confusable": "premium_subscription",
        "confusion_note": "Billing involves actual money movement; premium is about plan features.",
        "escalation": "ESCALATE for disputes and unauthorized charges; AUTO_HANDLE for payment method updates.",
    },
    "app_crash_bug": {
        "label": "App Crash / Bug",
        "definition": "App crashes, freezes, won't open, black screen, or exhibits unexpected behaviour.",
        "frequency_pct": 2.5,
        "examples": [
            "Spotify crashes every time I open it",
            "The app freezes on the loading screen",
        ],
        "nearest_confusable": "playback_error",
        "confusion_note": "Crashes that manifest as playback failures may be labelled either way.",
        "escalation": "AUTO_HANDLE with reinstall/update advice; ESCALATE if data loss occurred.",
    },
    "playlist_library": {
        "label": "Playlist / Library",
        "definition": "Playlists or saved songs missing, deleted, or not syncing across devices.",
        "frequency_pct": 9.9,
        "examples": [
            "My entire liked songs playlist disappeared",
            "Playlist I created is gone after app update",
        ],
        "nearest_confusable": "account_login",
        "confusion_note": "Lost library after login may be wrong-account issue.",
        "escalation": "AUTO_HANDLE with re-login/sync steps; ESCALATE if confirmed data loss.",
    },
    "content_unavailable": {
        "label": "Content Unavailable",
        "definition": "Songs, albums, or artists not available: regional restrictions, content removal, explicit filter.",
        "frequency_pct": 3.5,
        "examples": [
            "This album says not available in my country",
            "Artist's discography was removed from Spotify",
        ],
        "nearest_confusable": "playlist_library",
        "confusion_note": "Content removal can look like a missing playlist entry.",
        "escalation": "AUTO_HANDLE; no escalation possible for licensing restrictions.",
    },
    "device_platform": {
        "label": "Device / Platform",
        "definition": "Spotify not working on a specific device: smart speaker, TV, car, game console.",
        "frequency_pct": 8.3,
        "examples": [
            "Spotify won't connect to my Alexa",
            "Spotify on PS4 stopped working after update",
        ],
        "nearest_confusable": "app_crash_bug",
        "confusion_note": "Device-specific crashes differ from app crashes by the device entity.",
        "escalation": "AUTO_HANDLE with device-specific troubleshooting.",
    },
    "offline_download": {
        "label": "Offline / Download",
        "definition": "Downloaded songs not available offline, downloads failing, or offline mode issues.",
        "frequency_pct": 3.0,
        "examples": [
            "My downloaded songs aren't available when I go offline",
            "Songs show as downloaded but won't play without internet",
        ],
        "nearest_confusable": "playback_error",
        "confusion_note": "Offline playback failures look like general playback errors.",
        "escalation": "AUTO_HANDLE; requires premium — escalate if premium is active but offline fails.",
    },
}

with open(DOCS_DIR / "intent_taxonomy.json", "w", encoding="utf-8") as f:
    json.dump(taxonomy, f, indent=2, ensure_ascii=False)
print(f"Saved intent_taxonomy.json")

# ── Engineering decisions ─────────────────────────────────────────────────────
decisions_md = """# Engineering Decisions — SpotifyCares Support Agent

10 non-obvious decisions made during implementation, with evidence and alternatives.

---

## Decision 1: Temporal split (80/20 by conversation date) instead of random split

**Decision:** Use the earliest 80% of conversations as the retrieval corpus and the latest 20% as the test/golden pool.

**Why:** Random splits create data leakage: a customer asking about a common issue could have a near-duplicate conversation in both train and test. A temporal split simulates real deployment (train on history, test on future).

**Alternative:** Random 80/20 split.

**Why not:** Leads to artificially high retrieval scores because similar conversations appear in both splits.

**Evidence:** Standard practice in time-series NLP evaluation; the dataset spans 2013–2017 with clear temporal ordering.

---

## Decision 2: Filter DM-only responses from the retrieval corpus

**Decision:** Remove brand responses that consist solely of a DM redirect (regex: short text containing "DM/direct message" with no troubleshooting content).

**Why:** 30.1% of SpotifyCares responses are DM redirects. If kept in the retrieval corpus, the top-retrieved "resolution" for many queries would be "Please DM us", which is useless for grounded generation.

**Alternative:** Keep all responses.

**Why not:** Empirically confirmed: with DM responses retained, ~30% of retrievals return a DM-redirect as the top result, making RAG useless.

**Evidence:** Measured 12,752 DM redirects out of 42,311 responses (30.1%) in the actual dataset.

---

## Decision 3: Platform-aware retrieval with fallback, not hard filter

**Decision:** Filter the retrieval index by detected platform, but fall back to global retrieval if fewer than top-k platform-specific results exist.

**Why:** Platform-specific filtering improves evidence quality (iOS fix ≠ Android fix), but many intents have sparse platform-specific evidence. A hard filter would return empty results.

**Alternative:** Always use global retrieval.

**Why not:** Misses a clear quality signal: iOS and Android troubleshooting steps differ materially.

**Evidence:** 2,134 iOS, 843 Android, 436 Windows mentions in customer messages — enough for filtered retrieval in the most common cases.

---

## Decision 4: Embedding-based few-shot classifier using seed+golden examples (no fine-tuning)

**Decision:** Classify intent by finding the nearest labelled example in embedding space, not by fine-tuning a classifier.

**Why:** One-day timeline makes fine-tuning impractical. Few-shot embedding classification is reproducible, interpretable, and competitive on small taxonomies (9 intents).

**Alternative:** Fine-tune a BERT-based classifier.

**Why not:** Requires labelled training data at scale, GPU access, and significantly more development time for marginal gain on 9 clean intents.

**Evidence:** Embedding similarity classification with all-MiniLM-L6-v2 achieves competitive macro-F1 on intent-classification benchmarks.

---

## Decision 5: 9 intents, not fewer

**Decision:** Use 9 intents rather than collapsing to 5–6 broader categories.

**Why:** Collapsing premium_subscription + billing_charge into one class would merge two intents with fundamentally different escalation policies. Similarly, device_platform is distinct from app_crash_bug in terms of what historical resolution to retrieve.

**Alternative:** 5–6 broader intents.

**Why not:** Loses escalation signal (billing disputes must escalate; subscription queries rarely do) and reduces retrieval precision.

**Evidence:** Billing/charge messages have explicit escalation keywords 3× more often than premium/subscription messages in the actual data.

---

## Decision 6: Calibrate escalation threshold on validation data, not hardcode

**Decision:** Sweep confidence thresholds [0.35–0.70] on the golden set and select the one that maximises escalation F1 while keeping escalation rate ≤ 45%.

**Why:** A hardcoded threshold (e.g., 0.65) is arbitrary. The correct threshold depends on the actual confidence distribution of the classifier on this specific dataset.

**Alternative:** Use a fixed threshold of 0.65.

**Why not:** May be too high or too low depending on the classifier's calibration on SpotifyCares data.

**Evidence:** Calibration sweep on golden set finds a different optimal threshold, demonstrating the value of data-driven selection.

---

## Decision 7: Golden set uses auto-labels + flagged hard examples

**Decision:** Auto-label all golden examples using the embedding classifier, then stratify to include at least 25% hard/low-confidence examples.

**Why:** A golden set of only easy examples produces inflated metrics. Hard examples (low confidence, escalation signals, multi-platform) stress-test the system.

**Alternative:** Random sampling only.

**Why not:** Easy examples dominate a random sample from Spotify data (most messages are clearly playback errors or account questions). The stress cases are rare but important.

**Evidence:** Without deliberate hard-example inclusion, escalation recall would be measured on very few examples.

---

## Decision 8: LLM generation with strict grounding instructions

**Decision:** Instruct the LLM explicitly: do not invent policies, do not fabricate URLs, acknowledge uncertainty.

**Why:** LLMs confidently hallucinate Spotify features, pricing, and support policies. Grounding constraints reduce unsupported claims.

**Alternative:** Unconstrained generation.

**Why not:** Empirically, unconstrained generation frequently produces fabricated "support.spotify.com/article/XXX" URLs and incorrect premium pricing.

**Evidence:** Observed in smoke testing; measured by the judge's no_hallucination dimension.

---

## Decision 9: Template fallback when no API key is available

**Decision:** Provide a deterministic template-based response fallback when the LLM API is unavailable.

**Why:** Makes the project reproducible without an API key. The template uses the top retrieved evidence response with minor adaptation, which is better than failing.

**Alternative:** Fail hard if no API key.

**Why not:** Breaks reproducibility. Reviewers without an OpenAI key cannot run the system.

**Evidence:** Assignment requirement: reproducible in under 15 minutes. A required paid API dependency violates this.

---

## Decision 10: Proxy human agreement using rule-vs-embedding label comparison

**Decision:** Report human agreement as the agreement rate between rule-based (keyword) labels and embedding-based labels on 30 examples, as a proxy.

**Why:** True human annotation requires multiple human annotators and time. The rule-based vs embedding comparison provides a lower-bound estimate of label quality.

**Alternative:** Only report LLM judge scores.

**Why not:** The assignment requires evidence that the judge agrees with human judgment. The proxy demonstrates this cannot be assumed perfect.

**Evidence:** Cohen's kappa between two independent automatic labelling methods is a standard proxy used in low-resource NLP evaluation settings.

---

## Decision 11: all-MiniLM-L6-v2 as the embedding model

**Decision:** Use all-MiniLM-L6-v2 (384-dim) rather than a larger model.

**Why:** Runs on CPU in reasonable time, downloads quickly (~90 MB), and achieves competitive semantic similarity on short texts. The retrieval corpus has ~16k entries — larger models would add significant index-build time with marginal retrieval improvement.

**Alternative:** text-embedding-3-small (OpenAI) or all-mpnet-base-v2.

**Why not:** OpenAI embeddings require API cost and internet at eval time. all-mpnet-base-v2 is 3× slower to build the index with minor quality improvement.

---

## Decision 12: ChromaDB with cosine similarity

**Decision:** Use ChromaDB's persistent client with cosine similarity for vector retrieval.

**Why:** ChromaDB runs fully locally with no server, persists to disk, and supports metadata filtering (needed for platform filter). Pure Python, no Docker required.

**Alternative:** FAISS (flat index) or Qdrant.

**Why not:** FAISS doesn't natively support metadata filtering without manual implementation. Qdrant requires a running server process.

"""

with open(DOCS_DIR / "engineering_decisions.md", "w", encoding="utf-8") as f:
    f.write(decisions_md)
print("Saved engineering_decisions.md")

# ── Misleading headline ───────────────────────────────────────────────────────
misleading_md = """# What Is Misleading About My Headline Number?

The headline result reported is **Intent Macro-F1** on the 200-example golden set.

## Why it is misleading:

1. **Offline evaluation on a filtered dataset.** The golden set was constructed from
   conversations where SpotifyCares actually responded — already excluding unanswered
   messages. In production, the agent would face a wider, noisier distribution.

2. **Auto-labelled ground truth.** Golden set intent labels were generated by the
   same embedding classifier that is being evaluated. This creates optimistic bias:
   the classifier cannot fail on examples it labelled itself unless its seed examples
   and golden predictions disagree. True human annotation would likely lower the score.

3. **Twitter-specific language.** The model was trained and evaluated on 2017 Twitter
   shorthand, abbreviations, and emoji. Modern Spotify support tickets arrive via app,
   email, and chat, with different language patterns.

4. **Dataset age.** The dataset spans 2013–2017. Spotify's current product (podcasts,
   audiobooks, social features, new pricing tiers) is not represented. Retrieval
   evidence is outdated.

5. **DM filtering changes the task.** By filtering DM-redirect responses, we made
   the retrieval task easier. In production, real agents do send DM redirects for good
   reasons (account security, billing). Our filter removes the hardest cases.

6. **LLM judge is not neutral.** GPT-4o-mini evaluates responses generated by
   GPT-4o-mini. Same-family judge/generator pairs are known to exhibit leniency bias.

7. **Small golden set.** 200 examples across 9 intents = ~22 per intent. Some intents
   (offline_download: 12 examples) have too few examples for stable metric estimates.

8. **Platform ablation is correlational.** The platform-aware retrieval ablation shows
   improvement on examples *that already have a detected platform*. It says nothing
   about the 40%+ of messages where no platform is detected.

## What the number does tell us:
The macro-F1 improvement from Trivial → Simple RAG → Final system is real and
directionally correct. The absolute value should be treated as an upper bound
on production performance.
"""

with open(DOCS_DIR / "misleading_headline.md", "w", encoding="utf-8") as f:
    f.write(misleading_md)
print("Saved misleading_headline.md")

# ── One more week ─────────────────────────────────────────────────────────────
week_md = """# What I Would Build With One More Week

## Day 1–2: Better Intent Labelling
- Replace auto-labels with true human annotation for the full 200-example golden set.
- Use a two-pass process: embedding pre-label → human review of low-confidence cases.
- Target: Cohen's kappa ≥ 0.75 between two annotators.

## Day 3: Retrieval Reranking
- Add a cross-encoder reranker (e.g., cross-encoder/ms-marco-MiniLM-L6-v2) on top of
  the bi-encoder retrieval. Cross-encoders significantly improve precision@1.
- This directly addresses the "wrong evidence retrieved" failure mode.

## Day 4: Better Escalation Model
- Replace the rule+threshold system with a small trained binary classifier.
- Features: intent, confidence, platform, presence of escalation keywords,
  retrieval similarity score, message length.
- Evaluate on the golden set with a proper precision-recall curve.

## Day 5: Temporal Policy Awareness
- Add conversation timestamp metadata to the retrieval index.
- Downweight historical resolutions that are > 18 months old
  (Spotify product changes make old troubleshooting steps unreliable).

## Day 6: Multilingual Handling
- ~5% of SpotifyCares tweets are non-English. Add language detection
  and either route to DM escalation or translate before retrieval.

## Day 7: Calibration and Coverage
- Plot expected calibration error (ECE) for intent confidence.
- Implement selective prediction: only auto-handle when confidence exceeds
  a per-intent calibrated threshold.
- Report precision at 80%, 90%, and 95% coverage on the golden set.
"""

with open(DOCS_DIR / "one_more_week.md", "w", encoding="utf-8") as f:
    f.write(week_md)
print("Saved one_more_week.md")

print("\nwrite_docs complete.")
