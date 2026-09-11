"""
Simple retrieval — token overlap (Jaccard) on a 500-example sample.
No embeddings. No FAISS. No TF-IDF matrix. Runs in < 1 second per query.

Public API:
    from retriever import retrieve_similar
    results = retrieve_similar("Spotify keeps stopping on Android", top_k=3)
    # returns list of dicts: {customer_msg, brand_response, platform, score}
"""
import json, re, time
from pathlib import Path

TRAIN_JSONL   = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\train.jsonl")
SAMPLE_JSONL  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\retrieval_sample.jsonl")
SAMPLE_SIZE   = 500

# ── build / load sample once ──────────────────────────────────────
def _build_sample():
    """Pick 500 rows from train.jsonl with a real brand_response."""
    rows, seen = [], set()
    with open(TRAIN_JSONL, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            msg  = r.get("customer_msg",    "").strip()
            resp = r.get("brand_response",  "").strip()
            if not msg or not resp or len(resp) < 20:
                continue
            if msg in seen:
                continue
            seen.add(msg)
            rows.append({
                "customer_msg":   msg,
                "brand_response": resp,
                "platform":       r.get("platform", "unknown"),
                "response_type":  r.get("response_type", "other"),
            })
            if len(rows) == SAMPLE_SIZE:
                break
    with open(SAMPLE_JSONL, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return rows

def _load_sample():
    if SAMPLE_JSONL.exists():
        rows = []
        with open(SAMPLE_JSONL, encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
        return rows
    return _build_sample()

_CORPUS = None

def _corpus():
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = _load_sample()
    return _CORPUS

# ── tokeniser ─────────────────────────────────────────────────────
_STOP = {
    "i","my","the","a","an","is","it","to","in","on","of","and","or",
    "but","with","for","at","me","we","you","they","he","she","this",
    "that","was","are","be","been","have","has","had","do","does","did",
    "not","no","so","if","as","from","by","am","im","its","can","cant",
    "wont","just","when","what","why","how","please","help","hi","hey",
    "spotify","spotifycares",
}

def _tokens(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(w for w in words if w not in _STOP and len(w) > 1)

# ── scoring ───────────────────────────────────────────────────────
def _jaccard(a_set, b_set):
    if not a_set or not b_set:
        return 0.0
    inter = len(a_set & b_set)
    union = len(a_set | b_set)
    return inter / union if union else 0.0

# ── public API ────────────────────────────────────────────────────
def retrieve_similar(query: str, top_k: int = 3,
                     platform_filter: str = "unknown") -> list:
    """
    Return top_k most similar historical (customer_msg, brand_response) pairs.

    Args:
        query           : incoming customer message
        top_k           : number of results
        platform_filter : if not 'unknown', boost same-platform hits

    Returns list of dicts with keys:
        customer_msg, brand_response, platform, score
    """
    corpus = _corpus()
    q_tok  = _tokens(query)

    scored = []
    for row in corpus:
        base  = _jaccard(q_tok, _tokens(row["customer_msg"]))
        # small platform boost
        boost = 0.15 if (platform_filter != "unknown"
                         and row["platform"] == platform_filter) else 0.0
        scored.append((base + boost, row))

    scored.sort(key=lambda x: -x[0])
    return [
        {
            "customer_msg":   r["customer_msg"],
            "brand_response": r["brand_response"],
            "platform":       r["platform"],
            "score":          round(s, 4),
        }
        for s, r in scored[:top_k]
    ]


# ── smoke test ────────────────────────────────────────────────────
if __name__ == "__main__":
    t0 = time.time()
    corpus = _corpus()
    load_t = time.time() - t0
    print(f"Corpus size : {len(corpus)}")
    print(f"Load time   : {load_t:.2f}s")

    query = "My Spotify keeps stopping on Android"
    t1 = time.time()
    results = retrieve_similar(query, top_k=3, platform_filter="android")
    query_t = time.time() - t1

    print(f"\nQuery : {query!r}")
    print(f"Query time : {query_t*1000:.1f}ms")
    print()
    for i, r in enumerate(results, 1):
        print(f"[{i}] score={r['score']:.4f}  platform={r['platform']}")
        print(f"     HIST_Q : {r['customer_msg'][:100]}")
        print(f"     HIST_A : {r['brand_response'][:120]}")
        print()

    print("retriever.py DONE.")
