"""
Intent classifier for SpotifyCares.

Two modes:
1. Rule-based (used in trivial baseline) — keyword patterns only.
2. Embedding-based few-shot (used in baselines 2 + final system):
   embed the message, find nearest labelled examples via cosine similarity.

The embedding-based classifier uses the labelled golden-set examples
(or a hand-seeded set of seed examples if golden set not yet built).
It does NOT fine-tune any model — this is intentional for reproducibility
and speed on a one-day timeline.

Every prediction returns:
  {
    "intent":     str,       # e.g. "playback_error"
    "confidence": float,     # 0–1
    "method":     str,       # "rule" | "embedding"
  }
"""

import re, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import INTENTS, INTENT_LABELS, DOCS_DIR

# ── Rule-based patterns (for trivial baseline) ────────────────────────────────
INTENT_PATTERNS = {
    "playback_error": re.compile(
        r'\b(play|playing|song|music|skip|pause|stuck|won.?t play|not playing|'
        r'buffer|stream|audio|sound|no sound|keeps stopping|keeps pausing)\b', re.I),
    "account_login": re.compile(
        r'\b(log.?in|login|sign.?in|password|forgot|reset.?pass|'
        r'can.?t access|locked out|account.*access|verify)\b', re.I),
    "premium_subscription": re.compile(
        r'\b(premium|subscri|free trial|upgrade|cancel.*subscri|'
        r'subscri.*cancel|plan|student plan|family plan|duo plan)\b', re.I),
    "billing_charge": re.compile(
        r'\b(charge|charg|bill|payment|refund|invoice|price|cost|paid|fee|'
        r'money|transaction|receipt|credit card|debit)\b', re.I),
    "app_crash_bug": re.compile(
        r'\b(crash|freeze|frozen|not work|won.?t open|bug|broken|error|'
        r'glitch|keeps closing|shut.*down|force.*close|black screen)\b', re.I),
    "playlist_library": re.compile(
        r'\b(playlist|library|saved|album|songs.?gone|disappeared|deleted|'
        r'missing.*song|sync|liked songs|my music|collection)\b', re.I),
    "content_unavailable": re.compile(
        r'\b(not available|unavailable|region|country|removed|taken down|'
        r'can.?t find|no longer|artist.*gone|album.*gone|explicit)\b', re.I),
    "device_platform": re.compile(
        r'\b(android|ios|iphone|ipad|windows|mac|linux|car|chromecast|'
        r'ps[34]|playstation|tv|alexa|echo|sonos|speaker|watch|'
        r'carplay|android.?auto|roku|firetv)\b', re.I),
    "offline_download": re.compile(
        r'\b(offline|download|downloaded|save.*listen|listen.*offline|'
        r'saved.*song|cache)\b', re.I),
}

# Priority order (higher priority = checked first when multiple match)
INTENT_PRIORITY = [
    "billing_charge",
    "account_login",
    "premium_subscription",
    "app_crash_bug",
    "offline_download",
    "content_unavailable",
    "playlist_library",
    "device_platform",
    "playback_error",
]

def rule_classify(text: str) -> dict:
    """Keyword rule-based classifier. Used in trivial baseline."""
    scores = {}
    for intent in INTENT_PRIORITY:
        m = INTENT_PATTERNS[intent].search(text)
        if m:
            scores[intent] = 1.0
    if not scores:
        return {"intent": "playback_error", "confidence": 0.2, "method": "rule"}
    # return highest-priority match
    for intent in INTENT_PRIORITY:
        if intent in scores:
            return {"intent": intent, "confidence": 0.55, "method": "rule"}


# ── Embedding-based few-shot classifier ──────────────────────────────────────
# Seed examples — one per intent — used before golden set is built.
# After golden set is built, use_golden_seeds() loads real labelled examples.
SEED_EXAMPLES = {
    "playback_error":      "Spotify keeps buffering and won't play any songs",
    "account_login":       "I can't log into my Spotify account, forgot password",
    "premium_subscription":"I cancelled my premium but still being charged",
    "billing_charge":      "There's an unexpected charge on my card from Spotify",
    "app_crash_bug":       "The Spotify app crashes every time I open it",
    "playlist_library":    "My saved playlist disappeared from my library",
    "content_unavailable": "This album is not available in my country",
    "device_platform":     "Spotify is not working on my Alexa speaker",
    "offline_download":    "My downloaded songs are not available offline anymore",
}

class EmbeddingClassifier:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Loading embedding model: {model_name} ...", flush=True)
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.examples: list[dict] = []   # {text, intent, embedding}
        self._load_seeds()

    def _load_seeds(self):
        self.examples = []
        for intent, text in SEED_EXAMPLES.items():
            emb = self.model.encode(text, normalize_embeddings=True)
            self.examples.append({"text": text, "intent": intent, "emb": emb})

    def load_golden_seeds(self, golden_path: Path):
        """Replace seed examples with actual golden-set examples (more accurate)."""
        if not golden_path.exists():
            print("  [classifier] golden set not found, using seed examples")
            return
        with open(golden_path, encoding="utf-8") as f:
            rows = [json.loads(l) for l in f]
        # Use up to 20 examples per intent
        from collections import defaultdict
        by_intent = defaultdict(list)
        for r in rows:
            by_intent[r["intent"]].append(r["customer_msg"])
        self.examples = []
        for intent, msgs in by_intent.items():
            for msg in msgs[:20]:
                emb = self.model.encode(msg, normalize_embeddings=True)
                self.examples.append({"text": msg, "intent": intent, "emb": emb})
        print(f"  [classifier] loaded {len(self.examples)} golden seeds across "
              f"{len(by_intent)} intents", flush=True)

    def classify(self, text: str) -> dict:
        emb = self.model.encode(text, normalize_embeddings=True)
        sims = np.array([np.dot(emb, ex["emb"]) for ex in self.examples])
        top_idx  = int(np.argmax(sims))
        top_sim  = float(sims[top_idx])
        top_intent = self.examples[top_idx]["intent"]
        return {
            "intent":     top_intent,
            "confidence": round(top_sim, 4),
            "method":     "embedding",
        }

    def classify_batch(self, texts: list[str]) -> list[dict]:
        embs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        seed_embs = np.stack([ex["emb"] for ex in self.examples])
        sims = embs @ seed_embs.T   # (N, n_seeds)
        results = []
        for i, row_sims in enumerate(sims):
            top_idx = int(np.argmax(row_sims))
            results.append({
                "intent":     self.examples[top_idx]["intent"],
                "confidence": round(float(row_sims[top_idx]), 4),
                "method":     "embedding",
            })
        return results


# ── Singleton for reuse ───────────────────────────────────────────────────────
_classifier: EmbeddingClassifier | None = None

def get_classifier(golden_path: Path | None = None) -> EmbeddingClassifier:
    global _classifier
    if _classifier is None:
        from config import EMBED_MODEL
        _classifier = EmbeddingClassifier(EMBED_MODEL)
    if golden_path and golden_path.exists():
        _classifier.load_golden_seeds(golden_path)
    return _classifier


if __name__ == "__main__":
    # Quick smoke test
    clf = get_classifier()
    tests = [
        "Spotify crashes when I open it on my iPhone",
        "I was charged twice for premium this month",
        "My playlist is missing all songs",
        "Can't log in, forgot my password",
        "Song won't play, just keeps spinning",
    ]
    print("\nSmoke test:")
    for t in tests:
        r = clf.classify(t)
        print(f"  [{r['intent']:<25}  conf={r['confidence']:.2f}]  {t}")
