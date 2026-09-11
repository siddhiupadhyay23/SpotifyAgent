"""
HIVER ASSIGNMENT — ACTUAL DATA VERIFICATION
XboxSupport vs SpotifyCares
Run: python verify_brands.py
"""

import pandas as pd
import numpy as np
import re
from collections import defaultdict, Counter

CSV = r'C:\Users\Siddhi\Desktop\Hiver\twcs\twcs.csv'
BRANDS = ['XboxSupport', 'SpotifyCares']
SEP = "=" * 68

def sec(t): print(f"\n{SEP}\n  {t}\n{SEP}")
def hr():   print("-" * 68)

# ─────────────────────────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────────────────────────
sec("LOADING FULL DATASET")
df = pd.read_csv(CSV, dtype={
    'tweet_id': 'Int64',
    'in_response_to_tweet_id': 'float64',
    'response_tweet_id': 'object',
    'inbound': bool,
    'author_id': str,
    'text': str,
    'created_at': str
})
print(f"Total rows       : {len(df):,}")
print(f"Columns          : {list(df.columns)}")
print(f"Inbound (cust.)  : {df['inbound'].sum():,}")
print(f"Outbound (brand) : {(~df['inbound']).sum():,}")
df['created_at_dt'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
print(f"Date range       : {df['created_at_dt'].min()} → {df['created_at_dt'].max()}")

# top brands by outbound volume
top = df[~df['inbound']]['author_id'].value_counts().head(25)
print("\nTop 25 brands by outbound tweet count:")
for brand, cnt in top.items():
    marker = " ◄◄◄" if brand in BRANDS else ""
    print(f"  {brand:<30} {cnt:>7,}{marker}")

# ─────────────────────────────────────────────────────────────────
# FAST LOOKUP STRUCTURES
# ─────────────────────────────────────────────────────────────────
sec("BUILDING LOOKUP STRUCTURES")
# tweet_id -> row index for fast retrieval
id_to_idx = {row.tweet_id: i for i, row in df.iterrows() if pd.notna(row.tweet_id)}
# parent -> list of children
children = defaultdict(list)
for _, row in df.iterrows():
    p = row['in_response_to_tweet_id']
    if pd.notna(p):
        children[int(p)].append(int(row['tweet_id']))
print("Lookup structures ready.")

def get_thread(root_id, max_depth=30):
    """BFS to collect all tweet_ids in a thread from root."""
    visited, queue, result = set(), [root_id], []
    while queue and len(result) < max_depth:
        node = queue.pop(0)
        if node in visited: continue
        visited.add(node)
        result.append(node)
        for ch in children.get(node, []):
            queue.append(ch)
    return result

# ─────────────────────────────────────────────────────────────────
# PER-BRAND ANALYSIS
# ─────────────────────────────────────────────────────────────────
results = {}

for BRAND in BRANDS:
    sec(f"BRAND: {BRAND}")

    # ── raw counts ──────────────────────────────────────────────
    brand_out_df = df[df['author_id'] == BRAND]
    n_out = len(brand_out_df)

    # inbound tweets that brand replied to
    replied_to_ids = set(
        brand_out_df['in_response_to_tweet_id']
        .dropna().astype(int).tolist()
    )
    brand_in_df = df[df['tweet_id'].isin(replied_to_ids) & df['inbound']]
    n_in = len(brand_in_df)

    unique_custs = brand_in_df['author_id'].nunique()

    print(f"Outbound (brand tweets)   : {n_out:,}")
    print(f"Inbound (paired customer) : {n_in:,}")
    print(f"Unique customers served   : {unique_custs:,}")

    # date range
    out_dates = brand_out_df['created_at_dt'].dropna()
    if len(out_dates):
        print(f"Date range (outbound)     : {out_dates.min().date()} → {out_dates.max().date()}")

    # ── conversation reconstruction ──────────────────────────────
    print("\n--- Conversation Reconstruction ---")
    # Find root of each conversation the brand participated in
    root_ids = set()
    for pid in replied_to_ids:
        # walk up to find root
        node = pid
        for _ in range(20):
            if node not in id_to_idx: break
            row = df.iloc[id_to_idx[node]]
            p = row['in_response_to_tweet_id']
            if pd.isna(p): break
            node = int(p)
        root_ids.add(node)

    threads = []
    for root in root_ids:
        tid_list = get_thread(root)
        rows = []
        for tid in tid_list:
            if tid in id_to_idx:
                r = df.iloc[id_to_idx[tid]]
                rows.append({
                    'tweet_id': tid,
                    'author': r['author_id'],
                    'text': str(r['text']) if pd.notna(r['text']) else '',
                    'inbound': r['inbound'],
                    'created_at': r['created_at_dt']
                })
        # only keep threads where brand appears
        if any(r['author'] == BRAND for r in rows) and len(rows) >= 2:
            threads.append(rows)

    n_threads = len(threads)
    lengths = [len(t) for t in threads]
    n_multi = sum(1 for l in lengths if l >= 3)
    n_long  = sum(1 for l in lengths if l >= 5)

    print(f"Reconstructed conversations    : {n_threads:,}")
    if lengths:
        print(f"Avg turns per conversation     : {np.mean(lengths):.2f}")
        print(f"Median turns                   : {np.median(lengths):.1f}")
        print(f"Max turns                      : {max(lengths)}")
        print(f"2-turn conversations            : {sum(l==2 for l in lengths):,} "
              f"({100*sum(l==2 for l in lengths)/n_threads:.1f}%)")
        print(f"3+ turn conversations           : {n_multi:,} "
              f"({100*n_multi/n_threads:.1f}%)")
        print(f"5+ turn conversations           : {n_long:,} "
              f"({100*n_long/n_threads:.1f}%)")

    # length distribution
    dist = Counter(lengths)
    print("Length distribution:")
    for l in sorted(dist)[:8]:
        bar = '█' * min(int(dist[l]/max(dist.values())*30), 30)
        print(f"  {l:>2} turns: {dist[l]:>5,}  {bar}")

    # ── sample conversations ────────────────────────────────────
    print(f"\n--- 3 Sample Conversations ({BRAND}) ---")
    # pick varied: short, medium, long
    sorted_threads = sorted(threads, key=len)
    picks = []
    if sorted_threads:
        picks.append(sorted_threads[len(sorted_threads)//4])    # short
        picks.append(sorted_threads[len(sorted_threads)//2])    # medium
        picks.append(sorted_threads[min(-1, -len(sorted_threads)//5)])  # longer
    for idx, thread in enumerate(picks[:3]):
        print(f"\n  [Sample {idx+1} — {len(thread)} turns]")
        for turn in thread[:8]:
            role = "BRAND   " if turn['author'] == BRAND else "CUSTOMER"
            txt = turn['text'][:180].replace('\n', ' ')
            print(f"  [{role}] {txt}")

    # ── response quality classification ─────────────────────────
    print("\n--- Response Quality Classification ---")
    brand_responses = [t['text'] for thread in threads
                       for t in thread if t['author'] == BRAND and t['text'].strip()]

    DM_PAT       = re.compile(r'\bDM\b|direct.?message|private.?message|send us a (msg|message)|message us', re.I)
    TEMPLATE_PAT = re.compile(r"sorry to hear|we apologize|we'?re sorry|apologies for|thank you for (reaching|contacting)|thanks for (reaching|contacting)", re.I)
    TROUBLE_PAT  = re.compile(r'\b(try|restart|reboot|reset|clear.?cache|reinstall|re-install|uninstall|update|check|verify|enable|disable|toggle|settings|steps|follow|click|tap|go to|navigate|sign out|log out|logout)\b', re.I)
    LINK_PAT     = re.compile(r'https?://|bit\.ly|tinyurl|support\.|help\.', re.I)
    POLICY_PAT   = re.compile(r'\b(policy|terms|refund|eligible|within \d+.?day|compensation|process|submit|claim|appeal|review)\b', re.I)
    CLARIFY_PAT  = re.compile(r'\?')

    cats = {'DM redirect': 0, 'Generic template': 0, 'Troubleshooting steps': 0,
            'Link / resource': 0, 'Policy / process': 0,
            'Clarification question': 0, 'Other / low-info': 0}

    for resp in brand_responses:
        if DM_PAT.search(resp):
            cats['DM redirect'] += 1
        elif TEMPLATE_PAT.search(resp) and len(resp) < 130:
            cats['Generic template'] += 1
        elif TROUBLE_PAT.search(resp):
            cats['Troubleshooting steps'] += 1
        elif LINK_PAT.search(resp):
            cats['Link / resource'] += 1
        elif POLICY_PAT.search(resp):
            cats['Policy / process'] += 1
        elif CLARIFY_PAT.search(resp):
            cats['Clarification question'] += 1
        else:
            cats['Other / low-info'] += 1

    total_resp = max(len(brand_responses), 1)
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        bar = '█' * min(int(cnt/total_resp*40), 40)
        print(f"  {cat:<30} {cnt:>5,} ({100*cnt/total_resp:5.1f}%)  {bar}")

    useful = (cats['Troubleshooting steps'] + cats['Link / resource'] +
              cats['Policy / process'] + cats['Clarification question'])
    low    = cats['DM redirect'] + cats['Generic template'] + cats['Other / low-info']
    print(f"\n  ✓ USEFUL FOR RETRIEVAL : {useful:,} ({100*useful/total_resp:.1f}%)")
    print(f"  ✗ LOW-INFO / REDIRECT  : {low:,} ({100*low/total_resp:.1f}%)")

    # ── intent discovery from customer messages ──────────────────
    print("\n--- Intent Discovery (keyword frequency) ---")
    cust_msgs = [t['text'] for thread in threads
                 for t in thread if t['author'] != BRAND and t['text'].strip()]
    print(f"Customer messages analysed: {len(cust_msgs):,}")

    if BRAND == 'XboxSupport':
        intents = {
            'Error Code (structured)':
                r'\b(0x[0-9A-Fa-f]{4,}|E\d{3,4})\b',
            'Account / Ban / Suspension':
                r'\b(account|suspend|ban|banned|suspended|lock|locked|access)\b',
            'Download / Install / Update':
                r'\b(download|install|installing|patch|update|stuck at|slow download)\b',
            'Billing / Subscription (Gold/GamePass)':
                r'\b(charge|charged|billing|refund|subscription|payment|gold|gamepass|game.?pass|xbox live)\b',
            'Network / Multiplayer / Online':
                r'\b(connect|connection|online|network|nat|multiplayer|party|lag|disconnect|sign.?in)\b',
            'Game Content / DLC / Achievement':
                r'\b(achievement|dlc|content|missing|season.?pass|map.?pack|not.?showing|disappeared)\b',
            'Console / Hardware / Disc':
                r'\b(console|hardware|disc|disk|controller|kinect|hdmi|broken|repair|won.?t.?turn)\b',
            'Crash / Freeze / Performance':
                r'\b(crash|freeze|frozen|not.?launch|won.?t.?start|slow|performance|loading)\b',
            'App / Store / Dashboard':
                r'\b(app|dashboard|store|ui|menu|home|screen|update)\b',
            'Refund Request':
                r'\b(refund|money.?back|want.?my.?money|return)\b',
        }
    else:  # SpotifyCares
        intents = {
            'Playback Error':
                r'\b(play|playing|song|music|skip|pause|stuck|won.?t.?play|not.?playing|buffer|stream)\b',
            'Account / Login / Access':
                r'\b(log.?in|login|password|account|sign.?in|can.?t.?access|locked.?out|forgot)\b',
            'Premium / Subscription':
                r'\b(premium|subscri|plan|upgrade|free|cancel|renew)\b',
            'Billing / Charge':
                r'\b(charg|bill|payment|refund|invoice|price|cost|paid|fee)\b',
            'App Crash / Performance':
                r'\b(crash|freeze|not.?work|won.?t.?open|bug|broken|error|slow)\b',
            'Device / Platform':
                r'\b(android|ios|iphone|ipad|windows|mac|linux|car|chromecast|ps[34]|tv|alexa|speaker|watch)\b',
            'Playlist / Library / Sync':
                r'\b(playlist|library|saved|album|miss|disappear|deleted|gone|sync|songs.?gone)\b',
            'Content / Song Not Available':
                r'\b(available|region|country|not.?available|removed|missing|taken.?down|can.?t.?find|explicit)\b',
            'Offline / Download':
                r'\b(offline|download|downloaded|saved.?song)\b',
            'Ad / Free Tier':
                r'\b(\bad\b|ads|advertisement|advert|free.?tier|upgrade.?to)\b',
        }

    intent_hits = {}
    for name, pat in intents.items():
        hits = [m for m in cust_msgs if re.search(pat, m, re.I)]
        intent_hits[name] = hits

    print(f"\n  {'Intent':<45} {'Count':>6}  {'%':>5}  Sample")
    print(f"  {'-'*45} {'-'*6}  {'-'*5}  {'------'}")
    for name, hits in sorted(intent_hits.items(), key=lambda x: -len(x[1])):
        pct = 100*len(hits)/max(len(cust_msgs),1)
        sample = hits[0][:80].replace('\n',' ') if hits else '—'
        print(f"  {name:<45} {len(hits):>6,}  {pct:>4.1f}%  {sample!r}")

    # ── error-code specific analysis (Xbox) ────────────────────
    if BRAND == 'XboxSupport':
        print("\n--- Error Code Deep Dive ---")
        ec_pat = re.compile(r'\b(0x[0-9A-Fa-f]{4,}|E\d{3,4})\b')
        ec_msgs = [(m, ec_pat.findall(m)) for m in cust_msgs if ec_pat.search(m)]
        all_codes = [c for _, codes in ec_msgs for c in codes]
        print(f"Messages with error codes : {len(ec_msgs):,} "
              f"({100*len(ec_msgs)/max(len(cust_msgs),1):.2f}% of customer msgs)")
        print(f"Total error code mentions : {len(all_codes):,}")
        print(f"Unique error codes        : {len(set(all_codes)):,}")
        if all_codes:
            top_ec = Counter(all_codes).most_common(10)
            print("Top 10 error codes:")
            for code, cnt in top_ec:
                print(f"  {code:<20} {cnt:>4,}x")
        if ec_msgs[:3]:
            print("Sample error-code tweets:")
            for msg, codes in ec_msgs[:3]:
                print(f"  codes={codes}  msg={msg[:130]!r}")

    # ── platform / entity signals (Spotify) ────────────────────
    if BRAND == 'SpotifyCares':
        print("\n--- Platform Entity Deep Dive ---")
        platforms = {
            'Android': r'\bandroid\b',
            'iOS/iPhone': r'\b(ios|iphone|ipad)\b',
            'Windows': r'\bwindows\b',
            'Mac/MacOS': r'\b(mac|macos|macbook)\b',
            'Smart Speaker': r'\b(alexa|echo|google.?home|sonos)\b',
            'Smart TV': r'\b(tv|smart.?tv|chromecast|firetv|fire.?stick)\b',
            'PlayStation': r'\bps[34]\b|\bplaystation\b',
            'Car/Auto': r'\b(car|vehicle|auto)\b',
        }
        print(f"  {'Platform':<25} {'Count':>6}  {'%':>5}")
        for plat, pat in platforms.items():
            n = sum(1 for m in cust_msgs if re.search(pat, m, re.I))
            print(f"  {plat:<25} {n:>6,}  {100*n/max(len(cust_msgs),1):>4.1f}%")

        # Check for multi-platform ambiguity
        multi_platform = [m for m in cust_msgs
                          if sum(1 for pat in platforms.values()
                                 if re.search(pat, m, re.I)) >= 2]
        print(f"\n  Messages mentioning 2+ platforms: {len(multi_platform):,} "
              f"({100*len(multi_platform)/max(len(cust_msgs),1):.1f}%)")

    # ── escalation signals ──────────────────────────────────────
    print("\n--- Escalation Signal Detection ---")
    esc_patterns = {
        'DM redirect by agent': DM_PAT,
        'Security / hack / unauthorized': re.compile(
            r'\b(secur|hack|hacked|compromis|unauthor|stole|stolen|fraud)\b', re.I),
        'Billing dispute / charge dispute': re.compile(
            r'\b(unauthori[sz]ed.?charge|chargeback|dispute|wrong.?charge|overcharg)\b', re.I),
        'Urgency signal': re.compile(
            r'\b(urgent|asap|emergency|right.?now|immediately|help.?me.?now|please.?help)\b', re.I),
        'Account locked/banned': re.compile(
            r'\b(account.*(lock|ban|suspend)|ban|banned|suspended|cannot.?access)\b', re.I),
        'Explicit frustration / threat': re.compile(
            r'\b(lawyer|legal|report|sue|news|refund.?or|never.?again|cancel.?everything)\b', re.I),
    }
    print(f"  Source: customer messages ({len(cust_msgs):,} total)")
    for sig, pat in esc_patterns.items():
        n = sum(1 for m in cust_msgs if pat.search(m))
        print(f"  {sig:<45} {n:>5,}  ({100*n/max(len(cust_msgs),1):.1f}%)")

    # ── golden set feasibility ──────────────────────────────────
    print("\n--- Golden Set Feasibility ---")
    useful_threads = [t for t in threads
                      if any(TROUBLE_PAT.search(turn['text']) or LINK_PAT.search(turn['text'])
                             for turn in t if turn['author'] == BRAND)]
    print(f"Threads with useful brand response : {len(useful_threads):,}")
    print(f"Recommended golden set size        : 200")
    feasible = len(useful_threads) >= 400
    print(f"Feasible (≥400 useful threads)?    : {'✓ YES' if feasible else '✗ MARGINAL'}")
    if feasible:
        print(f"  → Can sample 2× the target (safety margin exists)")

    # ── retrieval corpus estimate ───────────────────────────────
    print("\n--- Retrieval Corpus Estimate ---")
    retrieval_pairs = [(t[i]['text'], t[i+1]['text'])
                       for t in threads
                       for i in range(len(t)-1)
                       if t[i]['author'] != BRAND and t[i+1]['author'] == BRAND
                       and TROUBLE_PAT.search(t[i+1]['text'])]
    print(f"Usable (question, resolution) pairs: {len(retrieval_pairs):,}")

    # save summary
    results[BRAND] = {
        'n_out': n_out,
        'n_in': n_in,
        'unique_custs': unique_custs,
        'n_threads': n_threads,
        'n_multi': n_multi,
        'n_long': n_long,
        'avg_len': float(np.mean(lengths)) if lengths else 0,
        'useful_responses': useful,
        'low_info': low,
        'useful_pct': 100*useful/total_resp,
        'dm_pct': 100*cats['DM redirect']/total_resp,
        'useful_threads': len(useful_threads),
        'retrieval_pairs': len(retrieval_pairs),
        'top_intent': max(intent_hits.items(), key=lambda x: len(x[1]))[0] if intent_hits else 'N/A',
        'error_codes': len(ec_msgs) if BRAND == 'XboxSupport' else None,
    }

# ─────────────────────────────────────────────────────────────────
# PHASE 12 — HEAD-TO-HEAD SCORING
# ─────────────────────────────────────────────────────────────────
sec("PHASE 12 — HEAD-TO-HEAD SCORING")

rx = results['XboxSupport']
rs = results['SpotifyCares']

def score_volume(n):
    if n >= 30000: return 10
    if n >= 20000: return 9
    if n >= 15000: return 8
    if n >= 10000: return 7
    if n >= 5000:  return 6
    if n >= 2000:  return 5
    return 3

def score_quality(pct_useful):
    if pct_useful >= 55: return 10
    if pct_useful >= 45: return 9
    if pct_useful >= 35: return 8
    if pct_useful >= 25: return 7
    if pct_useful >= 15: return 6
    return 4

def score_dm(dm_pct):
    # lower dm = better (inverted)
    if dm_pct <= 10: return 10
    if dm_pct <= 20: return 8
    if dm_pct <= 30: return 7
    if dm_pct <= 40: return 6
    if dm_pct <= 50: return 5
    return 3

criteria = [
    # (criterion, xbox_raw, spotify_raw, weight)
    ("Data volume (outbound tweets)",         rx['n_out'],            rs['n_out'],            0.08),
    ("Data volume (convo pairs)",             rx['n_in'],             rs['n_in'],             0.08),
    ("Reconstructed conversations",           rx['n_threads'],        rs['n_threads'],        0.10),
    ("Multi-turn (3+) conversations",         rx['n_multi'],          rs['n_multi'],          0.08),
    ("Useful response % (retrieval quality)", rx['useful_pct'],       rs['useful_pct'],       0.12),
    ("DM-redirect % (lower=better, inverted)",100-rx['dm_pct'],       100-rs['dm_pct'],       0.10),
    ("Useful threads (golden set)",           rx['useful_threads'],   rs['useful_threads'],   0.10),
    ("Retrieval pairs",                       rx['retrieval_pairs'],  rs['retrieval_pairs'],  0.08),
    ("Avg conversation length",               rx['avg_len'],          rs['avg_len'],          0.06),
]

print(f"\n  {'Criterion':<45} {'Xbox':>8} {'Spotify':>8}  Winner")
print(f"  {'-'*45} {'-'*8} {'-'*8}  {'-'*10}")

xbox_weighted = 0.0
spot_weighted = 0.0
total_w = 0.0

for crit, xv, sv, w in criteria:
    # normalise to 0-10 scale using ratio
    mx = max(xv, sv, 1)
    xn = round(10 * xv / mx, 1)
    sn = round(10 * sv / mx, 1)
    winner = "Xbox" if xv > sv else ("Spotify" if sv > xv else "Tie")
    print(f"  {crit:<45} {xn:>8.1f} {sn:>8.1f}  {winner}")
    xbox_weighted += xn * w
    spot_weighted += sn * w
    total_w += w

print(f"\n  {'WEIGHTED SCORE':<45} {xbox_weighted:>8.2f} {spot_weighted:>8.2f}")

# Add qualitative factors
qual_factors = [
    ("India / global familiarity",        6, 9,  0.07),
    ("Daily use relevance",               7, 9,  0.05),
    ("Intent separability (qualitative)", 8, 9,  0.06),
    ("Technical depth (error codes etc)", 8, 7,  0.06),
    ("Escalation policy richness",        8, 7,  0.06),
    ("Distinctiveness / anti-cloning",    7, 4,  0.08),
    ("Interview memorability",            7, 7,  0.05),
    ("Implementation feasibility",        8, 9,  0.05),
]
print(f"\n  Qualitative factors (expert scoring):")
for crit, xv, sv, w in qual_factors:
    winner = "Xbox" if xv > sv else ("Spotify" if sv > xv else "Tie")
    print(f"  {crit:<45} {xv:>8} {sv:>8}  {winner}")
    xbox_weighted += xv * w
    spot_weighted += sv * w

print(f"\n  {'FINAL WEIGHTED SCORE (all factors)':<45} {xbox_weighted:>8.2f} {spot_weighted:>8.2f}")

winner = "XboxSupport" if xbox_weighted > spot_weighted else "SpotifyCares"
margin = abs(xbox_weighted - spot_weighted)
print(f"\n  ► WINNER: {winner}  (margin: {margin:.2f})")

# ─────────────────────────────────────────────────────────────────
# PHASE 13 — FINAL DECISION
# ─────────────────────────────────────────────────────────────────
sec("PHASE 13 — FINAL DECISION")

xr = results['XboxSupport']
sr = results['SpotifyCares']

print(f"""
FINAL WINNER    : {winner}
CONFIDENCE      : see score above

━━ ACTUAL MEASURED DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                           XboxSupport       SpotifyCares
─────────────────────────────────────────────────────────────────
Outbound (brand) tweets  : {xr['n_out']:>10,}    {sr['n_out']:>10,}
Paired inbound tweets    : {xr['n_in']:>10,}    {sr['n_in']:>10,}
Unique customers         : {xr['unique_custs']:>10,}    {sr['unique_custs']:>10,}
Reconstructed convos     : {xr['n_threads']:>10,}    {sr['n_threads']:>10,}
Multi-turn (3+) convos   : {xr['n_multi']:>10,}    {sr['n_multi']:>10,}
5+ turn convos           : {xr['n_long']:>10,}    {sr['n_long']:>10,}
Avg conversation length  : {xr['avg_len']:>10.2f}    {sr['avg_len']:>10.2f}
Useful response rate     : {xr['useful_pct']:>9.1f}%    {sr['useful_pct']:>9.1f}%
DM-redirect rate         : {xr['dm_pct']:>9.1f}%    {sr['dm_pct']:>9.1f}%
Useful retrieval pairs   : {xr['retrieval_pairs']:>10,}    {sr['retrieval_pairs']:>10,}
Golden-set feasible      : {'YES' if xr['useful_threads']>=400 else 'MARGINAL':>10}    {'YES' if sr['useful_threads']>=400 else 'MARGINAL':>10}
Error codes in data      : {str(xr['error_codes']):>10}    {'N/A':>10}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
