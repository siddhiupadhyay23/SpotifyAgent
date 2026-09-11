"""
Build ChromaDB vector index from retrieval_corpus.jsonl.
Creates two collections:
  spotify_global   - all pairs (simple RAG baseline)
  spotify_platform - same pairs with platform metadata (final system)
Run: python build_index.py
"""
import json, sys
from pathlib import Path

CORPUS  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\retrieval_corpus.jsonl")
CHROMA  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\retrieval\chroma_db")
MODEL   = "all-MiniLM-L6-v2"
BATCH   = 2000

CHROMA.mkdir(parents=True, exist_ok=True)

print("Loading corpus ...", flush=True)
pairs = []
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        pairs.append(json.loads(line))
print(f"  {len(pairs):,} pairs")

print(f"Loading embedding model: {MODEL} ...", flush=True)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer(MODEL)

texts = [p.get("customer_msg","")[:500] for p in pairs]
print(f"Embedding {len(texts):,} messages ...", flush=True)
embeddings = model.encode(texts, batch_size=256, show_progress_bar=True,
                          normalize_embeddings=True)
print(f"  shape: {embeddings.shape}")

import chromadb
client = chromadb.PersistentClient(path=str(CHROMA))

for name in ["spotify_global","spotify_platform"]:
    try: client.delete_collection(name)
    except Exception: pass

col_g = client.create_collection("spotify_global",   metadata={"hnsw:space":"cosine"})
col_p = client.create_collection("spotify_platform", metadata={"hnsw:space":"cosine"})

ids_buf, docs_buf, embs_buf, meta_buf = [], [], [], []

for i,(pair,emb) in enumerate(zip(pairs, embeddings)):
    uid  = f"p{i}"
    meta = {
        "platform":       pair.get("platform","unknown"),
        "response_type":  pair.get("response_type","other"),
        "brand_response": pair.get("brand_response","")[:500],
    }
    ids_buf.append(uid)
    docs_buf.append(pair.get("customer_msg","")[:500])
    embs_buf.append(emb.tolist())
    meta_buf.append(meta)

    if len(ids_buf) == BATCH or i == len(pairs)-1:
        col_g.add(ids=ids_buf, documents=docs_buf,
                  embeddings=embs_buf, metadatas=meta_buf)
        col_p.add(ids=ids_buf, documents=docs_buf,
                  embeddings=embs_buf, metadatas=meta_buf)
        ids_buf, docs_buf, embs_buf, meta_buf = [], [], [], []
        print(f"  indexed {min(i+1,len(pairs)):,}/{len(pairs):,}", end="\r", flush=True)

print(f"\nspotify_global   : {col_g.count():,}")
print(f"spotify_platform : {col_p.count():,}")

# Quick sanity check
qemb = model.encode(["spotify crashes on android"], normalize_embeddings=True)[0].tolist()
res  = col_g.query(query_embeddings=[qemb], n_results=2,
                   include=["documents","metadatas","distances"])
print("\nSanity query: 'spotify crashes on android'")
for doc,meta,dist in zip(res["documents"][0],res["metadatas"][0],res["distances"][0]):
    print(f"  sim={1-dist:.3f} plat={meta['platform']}  q={doc[:70]}")
    print(f"           a={meta['brand_response'][:70]}")

print("\nbuild_index DONE.")
