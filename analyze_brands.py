"""
HIVER ASSIGNMENT — ACTUAL DATA VERIFICATION SCRIPT
===================================================
Runs the full Phase 1–12 analysis on twcs.csv once it is available.
Run: python analyze_brands.py

Requires: twcs.csv in the same directory as this script.
Install deps: pip install pandas numpy scikit-learn sentence-transformers tqdm
"""

import os, sys, re
import pandas as pd
import numpy as np
from collections import Counter, defaultdict
from datetime import datetime

CSV_PATH = os.path.join(os.path.dirname(__file__), 'twcs.csv')

# ── helper ────────────────────────────────────────────────────────────────────
SEP = "=" * 70

def section(title):
    print(f"\n{SEP}\n{title}\n{SEP}")

def hr():
    print("-" * 70)

# ── STEP 0: verify file ───────────────────────────────────────────────────────
section("STEP 0: FILE VERIFICATION")

if not os.path.exists(CSV_PATH):
    print(f"ERROR: twcs.csv NOT FOUND at {CSV_PATH}")
    print("\nTo download the dataset:")
    print("  Option A (Kaggle CLI, requires kaggle.json):")
    print("    python -m kaggle datasets download -d thoughtvector/customer-support-on-twitter --unzip -p .")
    print("\n  Option B (manual):")
    print("    1. Visit https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter")
    print("    2. Download the zip, extract twcs.csv to:", os.path.dirname(CSV_PATH))
    print("\nRe-run this script after placing twcs.csv in the Hiver folder.")
    sys.exit(1)

size_bytes = os.path.getsize(CSV_PATH)
size_mb = size_bytes / (1024 * 1024)
print(f"File found: {CSV_PATH}")
print(f"File size : {size_mb:.1f} MB ({size_bytes:,} bytes)")

# ── load ──────────────────────────────────────────────────────────────────────
section("LOADING DATASET")
print("Reading CSV (this may take 10–20 seconds for ~400 MB file)...")

df = pd.read_csv(CSV_PATH)
print(f"Rows    : {len(df):,}")
print(f"Columns : {list(df.columns)}")
print(f"\nDtypes:\n{df.dtypes}")
print(f"\nNull counts:\n{df.isnull().sum()}")
print(f"\nSample rows:")
print(df.head(3).to_string())

# Confirm it is the right dataset
assert 'text' in df.columns, "ERROR: 'text' column missing — wrong dataset"
assert 'author_id' in df.columns, "ERROR: 'author_id' column missing"
print("\n✓ Dataset confirmed as Customer Support on Twitter (twcs.csv)")

# ── date range ────────────────────────────────────────────────────────────────
if 'created_at' in df.columns:
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
    valid_dates = df['created_at'].dropna()
    print(f"\nDate range: {valid_dates.min()} → {valid_dates.max()}")

# ── inbound / outbound split ──────────────────────────────────────────────────
section("DATASET-WIDE OVERVIEW")

# inbound = True means the tweet is FROM a customer TO a company
# (Kaggle dataset: inbound=True means customer message)
if 'inbound' in df.columns:
    n_inbound = df['inbound'].sum()
    n_outbound = (~df['inbound']).sum()
    print(f"Total tweets      : {len(df):,}")
    print(f"Inbound (customer): {n_inbound:,} ({100*n_inbound/len(df):.1f}%)")
    print(f"Outbound (brand)  : {n_outbound:,} ({100*n_outbound/len(df):.1f}%)")

# unique companies
company_counts = df[~df['inbound']]['author_id'].value_counts()
print(f"\nUnique support accounts: {len(company_counts)}")
print("\nTop 20 by outbound tweet count:")
print(company_counts.head(20).to_string())

# ── PHASE 1: brand-level stats ────────────────────────────────────────────────
BRANDS = ['XboxSupport', 'SpotifyCares']

for brand in BRANDS:
    section(f"PHASE 1: {brand} — RAW STATISTICS")

    # outbound = tweets sent BY the brand
    brand_out = df[df['author_id'] == brand]
    # inbound  = customer tweets that the brand responded to
    responded_ids = set(brand_out['in_response_to_tweet_id'].dropna().astype(int))
    brand_in  = df[(df['inbound'] == True) & (df['tweet_id'].isin(responded_ids))]
    # also get all inbound tweets that mention brand (some may not be in responded_ids)
    all_brand_in = df[(df['inbound'] == True) & (
        df['text'].str.contains(brand, case=False, na=False) |
        df['in_response_to_tweet_id'].isin(brand_out['tweet_id'])
    )]

    print(f"Outbound (brand) tweets : {len(brand_out):,}")
    print(f"Inbound paired tweets   : {len(brand_in):,}")
    print(f"Unique customers served : {brand_in['author_id'].nunique():,}")

    # date range for this brand
    if 'created_at' in df.columns:
        brand_dates = brand_out['created_at'].dropna()
        if len(brand_dates) > 0:
            print(f"Date range (outbound)   : {brand_dates.min()} → {brand_dates.max()}")

    # ── conversation reconstruction ──────────────────────────────────────────
    section(f"PHASE 2: {brand} — CONVERSATION RECONSTRUCTION")

    # Build conversation threads by chaining in_response_to_tweet_id
    # Map tweet_id -> row for fast lookup
    tweet_map = df.set_index('tweet_id').to_dict('index')

    def get_thread_root(tweet_id, tweet_map, max_depth=20):
        """Walk up in_response_to chain to find root tweet."""
        visited = set()
        tid = tweet_id
        for _ in range(max_depth):
            if tid in visited or tid not in tweet_map:
                break
            visited.add(tid)
            parent = tweet_map[tid].get('in_response_to_tweet_id')
            if pd.isna(parent) or parent is None:
                break
            tid = int(parent)
        return tid

    def get_thread(root_id, tweet_map, max_depth=30):
        """Get all tweets in a thread, sorted by created_at."""
        thread = []
        stack = [root_id]
        visited = set()
        # Build child map
        child_map = defaultdict(list)
        for tid, row in tweet_map.items():
            parent = row.get('in_response_to_tweet_id')
            if not pd.isna(parent) and parent is not None:
                child_map[int(parent)].append(tid)

        # BFS from root
        queue = [root_id]
        while queue and len(thread) < max_depth:
            node = queue.pop(0)
            if node in visited or node not in tweet_map:
                continue
            visited.add(node)
            thread.append(node)
            for child in child_map.get(node, []):
                queue.append(child)
        return thread

    # Get root tweets for this brand (tweets by brand that are responses to customers)
    roots = set()
    for _, row in brand_out.iterrows():
        parent_id = row.get('in_response_to_tweet_id')
        if not pd.isna(parent_id) and parent_id is not None:
            root = get_thread_root(int(parent_id), tweet_map)
            roots.add(root)

    print(f"Reconstructable conversation roots: {len(roots):,}")

    # Reconstruct threads from roots
    threads = []
    for root_id in list(roots)[:5000]:  # cap at 5000 for speed
        thread_ids = get_thread(root_id, tweet_map)
        thread_rows = []
        for tid in thread_ids:
            if tid in tweet_map:
                r = tweet_map[tid]
                thread_rows.append({
                    'tweet_id': tid,
                    'author_id': r.get('author_id'),
                    'text': r.get('text', ''),
                    'inbound': r.get('inbound'),
                    'created_at': r.get('created_at'),
                })
        # Only keep threads that contain at least one brand tweet
        author_ids = [t['author_id'] for t in thread_rows]
        if brand in author_ids and len(thread_rows) >= 2:
            threads.append(thread_rows)

    print(f"Valid multi-turn threads (≥2 turns, brand involved): {len(threads):,}")

    # Thread length distribution
    lengths = [len(t) for t in threads]
    if lengths:
        print(f"Thread length — mean: {np.mean(lengths):.1f}, median: {np.median(lengths):.1f}, max: {max(lengths)}")
        len_dist = Counter(lengths)
        print("Length distribution:")
        for l in sorted(len_dist.keys())[:10]:
            print(f"  {l} turns: {len_dist[l]:,} threads ({100*len_dist[l]/len(threads):.1f}%)")
        pct_multi = 100 * sum(1 for l in lengths if l >= 3) / len(threads)
        print(f"% threads with 3+ turns: {pct_multi:.1f}%")

    # ── sample conversations ──────────────────────────────────────────────────
    print(f"\n--- SAMPLE CONVERSATIONS ({brand}) ---")
    sample_threads = sorted(threads, key=len, reverse=True)[:5]
    for i, thread in enumerate(sample_threads[:3]):
        print(f"\n[Thread {i+1} — {len(thread)} turns]")
        for turn in thread[:8]:
            role = "BRAND" if turn['author_id'] == brand else "CUSTOMER"
            text = (turn['text'] or '')[:200].replace('\n', ' ')
            print(f"  [{role}] {text}")

    # ── PHASE 3: intent discovery ─────────────────────────────────────────────
    section(f"PHASE 3: {brand} — INTENT DISCOVERY FROM DATA")

    customer_msgs = [t['text'] for thread in threads for t in thread
                     if t['author_id'] != brand and t['text']]

    # Keyword-frequency approach for intent detection
    print(f"Customer messages to analyse: {len(customer_msgs):,}")

    intent_patterns = {}
    if brand == 'XboxSupport':
        intent_patterns = {
            'Error Code': r'\b(0x[0-9a-fA-F]{6,}|E\d{3,4})\b',
            'Account / Suspension / Ban': r'\b(account|suspend|ban|banned|suspended|lock|locked)\b',
            'Download / Install': r'\b(download|install|stuck|installing|patch|update)\b',
            'Billing / Subscription': r'\b(charge|charged|billing|refund|subscription|payment|gold|gamepass|game pass)\b',
            'Network / Online / Multiplayer': r'\b(connect|connection|online|network|NAT|multiplayer|party|lag|disconnect)\b',
            'Achievement / Content': r'\b(achievement|dlc|content|missing|dlc|season pass|map pack)\b',
            'Console / Hardware': r'\b(console|hardware|disc|disk|controller|kinect|hdmi|broken|repair)\b',
            'Game Launch / Performance': r'\b(crash|freeze|frozen|launch|won.t start|slow|performance)\b',
            'App / Dashboard': r'\b(app|dashboard|ui|update|screen|menu|store)\b',
        }
    elif brand == 'SpotifyCares':
        intent_patterns = {
            'Playback Error': r'\b(play|playing|song|music|skip|pause|stuck|won.t play|not playing|buffer)\b',
            'Account / Login': r'\b(log.?in|login|password|account|sign.?in|can.?t access|locked out)\b',
            'Premium / Subscription Billing': r'\b(premium|charg|bill|subscri|payment|cancel|refund|price|plan|paid)\b',
            'App Crash / Performance': r'\b(crash|freeze|frozen|slow|bug|not working|won.t open|broken|error)\b',
            'Device / Platform': r'\b(android|ios|iphone|ipad|windows|mac|linux|car|chromecast|ps4|tv|alexa|speaker)\b',
            'Playlist / Library': r'\b(playlist|library|saved|song|album|miss|disappear|deleted|gone|sync)\b',
            'Content Availability': r'\b(available|region|country|not available|removed|missing|taken down|can.t find)\b',
            'Offline / Download': r'\b(offline|download|download.d|saved)\b',
            'Ad / Free Tier': r'\b(\bad\b|ads|advertisement|free|upgrade)\b',
        }

    print("\nKeyword-based intent frequency:")
    intent_freq = {}
    for intent, pattern in intent_patterns.items():
        matches = sum(1 for m in customer_msgs if re.search(pattern, m, re.IGNORECASE))
        intent_freq[intent] = matches
        print(f"  {intent:<40}: {matches:,} ({100*matches/max(len(customer_msgs),1):.1f}%)")

    # Check for error codes specifically (Xbox)
    if brand == 'XboxSupport':
        error_code_msgs = [m for m in customer_msgs if re.search(r'\b0x[0-9a-fA-F]{6,}|E\d{3,4}\b', m)]
        print(f"\nMessages with explicit error codes: {len(error_code_msgs):,} "
              f"({100*len(error_code_msgs)/max(len(customer_msgs),1):.1f}%)")
        if error_code_msgs:
            print("Sample error code messages:")
            for m in error_code_msgs[:5]:
                print(f"  → {m[:150]}")

    # ── PHASE 4: retrieval quality ────────────────────────────────────────────
    section(f"PHASE 4: {brand} — RETRIEVAL QUALITY ANALYSIS")

    brand_responses = [t['text'] for thread in threads for t in thread
                       if t['author_id'] == brand and t['text']]
    print(f"Brand response messages: {len(brand_responses):,}")

    # Classify responses
    dm_pattern       = r'\bDM\b|direct message|private message|send us a message|message us'
    template_pattern = r"sorry to hear|we apologize|we.re sorry|apologies for|thank you for (reaching|contacting)|thanks for (reaching|contacting)"
    trouble_pattern  = r'\b(try|restart|reset|clear cache|reinstall|update|check|verify|enable|disable|settings|follow|steps|click|tap)\b'
    link_pattern     = r'http[s]?://|bit\.ly|tinyurl'
    policy_pattern   = r'\b(policy|terms|refund|eligible|within \d+ day|compensation|process|submit|claim)\b'

    cats = {
        'DM redirect'        : 0,
        'Generic template'   : 0,
        'Troubleshooting'    : 0,
        'Link/resource'      : 0,
        'Policy/process'     : 0,
        'Useful clarification': 0,
        'Other/low-info'     : 0,
    }

    for resp in brand_responses:
        r = resp.lower()
        if re.search(dm_pattern, resp, re.IGNORECASE):
            cats['DM redirect'] += 1
        elif re.search(template_pattern, resp, re.IGNORECASE) and len(resp) < 120:
            cats['Generic template'] += 1
        elif re.search(trouble_pattern, resp, re.IGNORECASE):
            cats['Troubleshooting'] += 1
        elif re.search(link_pattern, resp, re.IGNORECASE):
            cats['Link/resource'] += 1
        elif re.search(policy_pattern, resp, re.IGNORECASE):
            cats['Policy/process'] += 1
        elif '?' in resp:
            cats['Useful clarification'] += 1
        else:
            cats['Other/low-info'] += 1

    total_resp = max(len(brand_responses), 1)
    print("\nResponse quality breakdown:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:<30}: {count:,} ({100*count/total_resp:.1f}%)")

    useful = cats['Troubleshooting'] + cats['Link/resource'] + cats['Policy/process'] + cats['Useful clarification']
    print(f"\nUSEFUL FOR RETRIEVAL: {useful:,} ({100*useful/total_resp:.1f}%)")
    print(f"LOW INFO / REDIRECT : {cats['DM redirect']+cats['Generic template']+cats['Other/low-info']:,} "
          f"({100*(cats['DM redirect']+cats['Generic template']+cats['Other/low-info'])/total_resp:.1f}%)")

    # ── PHASE 6: escalation signals ──────────────────────────────────────────
    section(f"PHASE 6: {brand} — ESCALATION SIGNALS")

    escalation_keywords = {
        'DM redirect (agent-initiated)': dm_pattern,
        'Security concern': r'\bsecur|hack|compromis|unauthor|fraud\b',
        'Legal/financial dispute': r'\blegal|lawyer|court|charge.?back|fraud|unauthorized charge\b',
        'Urgent/emergency': r'\burgent|emergency|right now|asap|immediately|help me now\b',
        'Account locked/banned': r'\bban|suspend|lock|account.*block\b',
    }

    print("Escalation-relevant signals in customer messages:")
    for sig, pat in escalation_keywords.items():
        n = sum(1 for m in customer_msgs if re.search(pat, m, re.IGNORECASE))
        print(f"  {sig:<40}: {n:,} ({100*n/max(len(customer_msgs),1):.1f}%)")

    # ── PHASE 7: golden set feasibility ──────────────────────────────────────
    section(f"PHASE 7: {brand} — GOLDEN SET FEASIBILITY")

    usable_threads = [t for t in threads if len(t) >= 2]
    print(f"Usable threads (≥2 turns)             : {len(usable_threads):,}")
    useful_threads = [t for t in usable_threads
                      if any(re.search(trouble_pattern, turn['text'] or '', re.IGNORECASE)
                             for turn in t if turn['author_id'] == brand)]
    print(f"Threads with troubleshooting response  : {len(useful_threads):,}")
    print(f"Recommended golden set: 200 examples")
    print(f"Feasible? {'YES' if len(useful_threads) >= 400 else 'MARGINAL — check volume'}")

    # ── summary ──────────────────────────────────────────────────────────────
    section(f"SUMMARY — {brand}")
    print(f"Brand outbound tweets       : {len(brand_out):,}")
    print(f"Paired inbound tweets       : {len(brand_in):,}")
    print(f"Reconstructed conversations : {len(threads):,}")
    print(f"Useful for retrieval corpus : {useful:,} responses ({100*useful/total_resp:.1f}%)")
    print(f"DM-redirect rate            : {100*cats['DM redirect']/total_resp:.1f}%")
    if lengths:
        print(f"Avg thread length           : {np.mean(lengths):.1f} turns")

print("\n" + SEP)
print("ANALYSIS COMPLETE")
print(SEP)
