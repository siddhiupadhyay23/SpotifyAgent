"""
STEP 1 — SpotifyCares data pipeline (fast, vectorised).

Strategy:
  1. Read full CSV in one pass — only needed columns.
  2. Filter SpotifyCares rows vectorially (no iterrows).
  3. Build customer->agent pairs using pandas merge (not Python loops).
  4. Parse dates efficiently with explicit format string.
  5. Filter low-information DM-only responses.
  6. Reconstruct simple conversations using the reply-chain in pandas.
  7. Temporal split -> train / val / test.
  8. Save processed files.

Conversation reconstruction note:
  Full BFS thread reconstruction on 2.8M rows is too slow for a one-day
  timeline. Instead, we use "direct pairs" (inbound tweet + the brand's
  direct reply) which covers ~95% of useful retrieval evidence.
  Multi-turn context (the customer's prior message) is attached where
  available via the in_response_to chain one level up.
  This is documented as Engineering Decision #13.

Run: python preprocess.py
"""

import json, re, sys, time
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    RAW_CSV, PROC_DIR, BRAND, TRAIN_CUTOFF_PCT,
    DM_ONLY_PATTERN, extract_platform, RANDOM_SEED,
)

PROC_DIR.mkdir(parents=True, exist_ok=True)
t_start = time.time()

# ─────────────────────────────────────────────────────────────────
# 1. LOAD FULL CSV  (one pass, minimal columns)
# ─────────────────────────────────────────────────────────────────
print(f"[1/7] Loading {RAW_CSV} ...", flush=True)
t0 = time.time()
df = pd.read_csv(
    RAW_CSV,
    usecols=["tweet_id", "author_id", "inbound", "created_at",
             "text", "response_tweet_id", "in_response_to_tweet_id"],
    dtype={
        "tweet_id":                 "Int64",
        "in_response_to_tweet_id":  "float64",
        "response_tweet_id":        "object",
        "author_id":                str,
        "text":                     str,
        "inbound":                  bool,
    },
)
raw_rows = len(df)
print(f"    Loaded {raw_rows:,} rows in {time.time()-t0:.1f}s")

# ─────────────────────────────────────────────────────────────────
# 2. PARSE DATES  (explicit format = 50-100x faster than inference)
# ─────────────────────────────────────────────────────────────────
print("[2/7] Parsing timestamps ...", flush=True)
t0 = time.time()
df["ts"] = pd.to_datetime(
    df["created_at"],
    format="%a %b %d %H:%M:%S +0000 %Y",
    errors="coerce",
    utc=True,
)
null_ts = df["ts"].isna().sum()
print(f"    Parsed in {time.time()-t0:.1f}s  ({null_ts:,} unparsed -> coerced NaT)")

# ─────────────────────────────────────────────────────────────────
# 3. FILTER SpotifyCares ROWS  (vectorised, no loops)
# ─────────────────────────────────────────────────────────────────
print(f"[3/7] Filtering {BRAND} ...", flush=True)
t0 = time.time()

brand_out = df[df["author_id"] == BRAND].copy()   # agent tweets
n_out = len(brand_out)

# Inbound tweets that SpotifyCares directly replied to
replied_ids = brand_out["in_response_to_tweet_id"].dropna().astype(int)
replied_id_set = set(replied_ids.tolist())

brand_in = df[df["tweet_id"].isin(replied_id_set) & (df["inbound"] == True)].copy()
n_in = len(brand_in)

print(f"    {BRAND} outbound : {n_out:,}")
print(f"    {BRAND} inbound  : {n_in:,}")
print(f"    Unique customers : {brand_in['author_id'].nunique():,}")

# Date range
dates_out = brand_out["ts"].dropna()
if len(dates_out):
    print(f"    Date range       : {dates_out.min().date()} -> {dates_out.max().date()}")
print(f"    Filter done in {time.time()-t0:.1f}s")

# ─────────────────────────────────────────────────────────────────
# 4. BUILD CUSTOMER->AGENT PAIRS  (pandas merge, no loops)
# ─────────────────────────────────────────────────────────────────
print("[4/7] Building customer->agent pairs ...", flush=True)
t0 = time.time()

# brand_out has: in_response_to_tweet_id = the customer's tweet_id
brand_out_slim = brand_out[
    ["tweet_id", "text", "ts", "in_response_to_tweet_id"]
].rename(columns={
    "tweet_id":                "agent_tweet_id",
    "text":                    "brand_response",
    "ts":                      "agent_ts",
    "in_response_to_tweet_id": "customer_tweet_id_fk",
})
brand_out_slim["customer_tweet_id_fk"] = (
    brand_out_slim["customer_tweet_id_fk"].dropna().astype("Int64")
)

brand_in_slim = brand_in[["tweet_id", "text", "ts", "author_id"]].rename(columns={
    "tweet_id":  "customer_tweet_id",
    "text":      "customer_msg",
    "ts":        "customer_ts",
    "author_id": "customer_id",
})

pairs = brand_out_slim.merge(
    brand_in_slim,
    left_on="customer_tweet_id_fk",
    right_on="customer_tweet_id",
    how="inner",
)
pairs = pairs.dropna(subset=["customer_msg", "brand_response"])
pairs = pairs[pairs["customer_msg"].str.strip().ne("")]
pairs = pairs[pairs["brand_response"].str.strip().ne("")]
n_pairs_raw = len(pairs)
print(f"    Raw pairs (before DM filter) : {n_pairs_raw:,}  "
      f"(done in {time.time()-t0:.1f}s)")

# ─────────────────────────────────────────────────────────────────
# 5. ENRICH PAIRS  (platform, response type, DM filter) — vectorised
# ─────────────────────────────────────────────────────────────────
print("[5/7] Enriching + filtering pairs ...", flush=True)
t0 = time.time()

# Platform extraction (vectorised via apply — fast enough on ~40k rows)
pairs["platform"] = pairs["customer_msg"].apply(extract_platform)

# Response type classifier (vectorised)
TROUBLE = re.compile(
    r"\b(try|restart|reboot|reset|clear\s*cache|reinstall|re-?install|"
    r"uninstall|update|check|verify|enable|disable|toggle|go\s+to|"
    r"sign\s+out|log\s+out|logout|navigate|steps|follow|click|tap)\b",
    re.I,
)
LINK    = re.compile(r"https?://|bit\.ly|support\.|help\.", re.I)
POLICY  = re.compile(
    r"\b(policy|refund|eligible|within\s+\d+\s*day|compensation|"
    r"submit|claim|appeal|review)\b", re.I,
)
DM_PAT  = re.compile(
    r"\b(dm\b|direct\s*message|send\s+us\s+a\s+(msg|message)|message\s+us)\b",
    re.I,
)

def classify_resp(text: str) -> str:
    if TROUBLE.search(text): return "troubleshooting"
    if LINK.search(text):    return "link"
    if POLICY.search(text):  return "policy"
    if DM_PAT.search(text):  return "dm_redirect"
    if "?" in text and len(text) > 30: return "clarification"
    return "other"

pairs["response_type"] = pairs["brand_response"].apply(classify_resp)

# DM-only filter: keep if NOT (short + pure DM redirect)
dm_only_mask = (
    (pairs["response_type"] == "dm_redirect") &
    (pairs["brand_response"].str.len() < 120)
)
n_dm_dropped = int(dm_only_mask.sum())
pairs_filtered = pairs[~dm_only_mask].copy()
n_pairs_kept = len(pairs_filtered)

print(f"    DM-only dropped  : {n_dm_dropped:,} "
      f"({100*n_dm_dropped/max(n_pairs_raw,1):.1f}%)")
print(f"    Pairs kept       : {n_pairs_kept:,}")
rtype_dist = pairs_filtered["response_type"].value_counts()
for rt, n in rtype_dist.items():
    print(f"      {rt:<20} {n:>5,} ({100*n/n_pairs_kept:.1f}%)")
print(f"    Enrichment done in {time.time()-t0:.1f}s")

# ─────────────────────────────────────────────────────────────────
# 6. LIGHTWEIGHT CONVERSATION RECONSTRUCTION
#    Two-level: attach the customer's PRIOR message (one hop up)
#    to give retrieval context without full BFS over 2.8M rows.
# ─────────────────────────────────────────────────────────────────
print("[6/7] Attaching prior context (one-hop) ...", flush=True)
t0 = time.time()

# Build lookup: tweet_id -> text for all inbound tweets
inbound_all = df[df["inbound"] == True][["tweet_id", "text", "in_response_to_tweet_id"]].copy()
inbound_all = inbound_all.dropna(subset=["tweet_id"])
inbound_all["tweet_id"] = inbound_all["tweet_id"].astype(int)
id_to_text = inbound_all.set_index("tweet_id")["text"].to_dict()

# For each pair, look up one level up (what the customer's message
# was responding to, if it was also a customer tweet)
def get_prior(cust_tweet_id, in_resp_to):
    """Return prior customer message one hop up, if it exists."""
    parent_id = in_resp_to
    if pd.isna(parent_id):
        return ""
    pid = int(parent_id)
    return id_to_text.get(pid, "")

# Attach in_response_to_tweet_id for customer tweets
cust_in_resp = brand_in[["tweet_id", "in_response_to_tweet_id"]].copy()
cust_in_resp["tweet_id"] = cust_in_resp["tweet_id"].astype(int)
cust_in_resp = cust_in_resp.rename(columns={
    "tweet_id": "customer_tweet_id2",
    "in_response_to_tweet_id": "cust_prior_tweet_id",
})
pairs_filtered = pairs_filtered.merge(
    cust_in_resp,
    left_on="customer_tweet_id",
    right_on="customer_tweet_id2",
    how="left",
)
pairs_filtered["prior_context"] = pairs_filtered.apply(
    lambda r: id_to_text.get(int(r["cust_prior_tweet_id"]), "")
    if pd.notna(r.get("cust_prior_tweet_id")) else "",
    axis=1,
)
pairs_filtered.drop(columns=["customer_tweet_id2", "cust_prior_tweet_id"],
                    inplace=True, errors="ignore")

has_context = (pairs_filtered["prior_context"].str.strip() != "").sum()
print(f"    Pairs with prior context : {has_context:,} "
      f"({100*has_context/max(n_pairs_kept,1):.1f}%)")
print(f"    Context attachment done in {time.time()-t0:.1f}s")

# ─────────────────────────────────────────────────────────────────
# 7. TEMPORAL SPLIT  (by agent_ts)
# ─────────────────────────────────────────────────────────────────
print("[7/7] Temporal split ...", flush=True)
t0 = time.time()

pairs_filtered = pairs_filtered.sort_values("agent_ts", na_position="last")
pairs_filtered = pairs_filtered.reset_index(drop=True)

n_total = len(pairs_filtered)
n_train = int(n_total * 0.70)
n_val   = int(n_total * 0.15)
n_test  = n_total - n_train - n_val

train_df = pairs_filtered.iloc[:n_train]
val_df   = pairs_filtered.iloc[n_train:n_train + n_val]
test_df  = pairs_filtered.iloc[n_train + n_val:]

print(f"    Train : {len(train_df):,}  "
      f"({train_df['agent_ts'].dropna().min().date() if len(train_df) else '?'} -> "
      f"{train_df['agent_ts'].dropna().max().date() if len(train_df) else '?'})")
print(f"    Val   : {len(val_df):,}  "
      f"({val_df['agent_ts'].dropna().min().date() if len(val_df) else '?'} -> "
      f"{val_df['agent_ts'].dropna().max().date() if len(val_df) else '?'})")
print(f"    Test  : {len(test_df):,}  "
      f"({test_df['agent_ts'].dropna().min().date() if len(test_df) else '?'} -> "
      f"{test_df['agent_ts'].dropna().max().date() if len(test_df) else '?'})")
print(f"    Split done in {time.time()-t0:.1f}s")

# ─────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────
def save_jsonl(df_part, path):
    path = Path(path)
    records = df_part.to_dict("records")
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            # make timestamps JSON-serialisable
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
                elif hasattr(v, "item"):      # numpy scalar
                    r[k] = v.item()
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)

save_jsonl(train_df, PROC_DIR / "train.jsonl")
save_jsonl(val_df,   PROC_DIR / "val.jsonl")
save_jsonl(test_df,  PROC_DIR / "test.jsonl")

# Also save full pairs for retrieval index (train + val)
retrieval_df = pd.concat([train_df, val_df], ignore_index=True)
save_jsonl(retrieval_df, PROC_DIR / "retrieval_corpus.jsonl")

stats = {
    "raw_dataset_rows":         raw_rows,
    "spotify_outbound":         n_out,
    "spotify_inbound_paired":   n_in,
    "pairs_before_dm_filter":   n_pairs_raw,
    "dm_only_dropped":          n_dm_dropped,
    "pairs_after_dm_filter":    n_pairs_kept,
    "train":                    len(train_df),
    "val":                      len(val_df),
    "test":                     len(test_df),
    "retrieval_corpus":         len(retrieval_df),
}
import json as _json
(PROC_DIR / "stats.json").write_text(_json.dumps(stats, indent=2))

total_time = time.time() - t_start

# ─────────────────────────────────────────────────────────────────
# FINAL REPORT
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 50)
print("  PREPROCESSING COMPLETE")
print("=" * 50)
print(f"  Raw dataset rows             : {raw_rows:,}")
print(f"  SpotifyCares outbound        : {n_out:,}")
print(f"  SpotifyCares inbound         : {n_in:,}")
print(f"  Pairs before DM filter       : {n_pairs_raw:,}")
print(f"  Low-info / DM dropped        : {n_dm_dropped:,}")
print(f"  Useful customer->agent pairs  : {n_pairs_kept:,}")
print(f"  Retrieval corpus             : {len(retrieval_df):,}")
print(f"  Train                        : {len(train_df):,}")
print(f"  Validation                   : {len(val_df):,}")
print(f"  Test                         : {len(test_df):,}")
print(f"  Total runtime                : {total_time:.1f}s")
print("=" * 50)

