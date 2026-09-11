"""
Hybrid retriever: TF-IDF cosine + Jaccard + platform boost.

Weights (configurable):
  TFIDF_W   = 0.70
  JACCARD_W = 0.20
  PLATFORM_W= 0.10
"""

import json, re, sys
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

SAMPLE  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\retrieval_sample.jsonl")

# ── weights ───────────────────────────────────────────────────────
TFIDF_W    = 0.70
JACCARD_W  = 0.20
PLATFORM_W = 0.10

# ── load + fit once ───────────────────────────────────────────────
def _load():
    rows = []
    with open(SAMPLE, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows

_corpus  = None
_tfidf   = None
_matrix  = None

def _init():
    global _corpus, _tfidf, _matrix
    if _corpus is not None:
        return
    _corpus = _load()
    texts   = [r["customer_msg"] for r in _corpus]
    _tfidf  = TfidfVectorizer(ngram_range=(1,2), max_features=10_000,
                               sublinear_tf=True, min_df=1)
    _matrix = _tfidf.fit_transform(texts)

# ── Jaccard helper ────────────────────────────────────────────────
_STOP = {
    "i","my","the","a","an","is","it","to","in","on","of","and","or",
    "but","with","for","at","me","we","you","they","this","that","was",
    "are","be","have","has","do","does","not","no","so","if","as","am",
    "im","its","can","cant","wont","just","hi","hey","spotify","spotifycares",
}
def _tok(t):
    return set(w for w in re.findall(r"[a-z0-9]+", t.lower())
               if w not in _STOP and len(w) > 1)

def _jaccard(a, b):
    if not a or not b: return 0.0
    i = len(a & b); u = len(a | b)
    return i/u if u else 0.0

# ── platform pattern ──────────────────────────────────────────────
_PLAT = re.compile(
    r"\b(android|ios|iphone|ipad|windows|mac|chromecast|alexa|echo|"
    r"sonos|speaker|tv|ps[34]|car|carplay|roku|web|browser)\b", re.I)

def _platform(text):
    m = _PLAT.search(text or "")
    return m.group(0).lower() if m else "unknown"

# ── public API ────────────────────────────────────────────────────
def retrieve_hybrid(query: str, top_k: int = 3) -> list[dict]:
    _init()
    q_plat = _platform(query)
    q_tok  = _tok(query)
    q_vec  = _tfidf.transform([query])

    # TF-IDF cosine scores for all corpus items
    tfidf_scores = cosine_similarity(q_vec, _matrix).flatten()

    results = []
    for idx, row in enumerate(_corpus):
        ts = float(tfidf_scores[idx])
        js = _jaccard(q_tok, _tok(row["customer_msg"]))
        c_plat = row.get("platform","unknown")
        ps = PLATFORM_W if (q_plat != "unknown" and q_plat == c_plat) else 0.0
        score = TFIDF_W * ts + JACCARD_W * js + ps
        results.append({
            "customer_msg":   row["customer_msg"],
            "brand_response": row["brand_response"],
            "platform":       c_plat,
            "tfidf_score":    round(ts, 4),
            "jaccard_score":  round(js, 4),
            "platform_match": c_plat == q_plat and q_plat != "unknown",
            "score":          round(score, 4),
        })

    results.sort(key=lambda x: -x["score"])
    return results[:top_k]


# ── quick smoke test ──────────────────────────────────────────────
if __name__ == "__main__":
    q = "My Spotify keeps stopping on Android"
    print(f"Query: {q!r}\n")
    for i, r in enumerate(retrieve_hybrid(q, top_k=3), 1):
        print(f"[{i}] score={r['score']:.4f}  "
              f"tfidf={r['tfidf_score']:.3f}  "
              f"jac={r['jaccard_score']:.3f}  "
              f"plat_match={r['platform_match']}  plat={r['platform']}")
        print(f"     Q: {r['customer_msg'][:90]}")
        print(f"     A: {r['brand_response'][:90]}")
