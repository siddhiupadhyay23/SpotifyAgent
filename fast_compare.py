"""
Fast XboxSupport vs SpotifyCares comparison.
Runs in ~3-5 minutes on the full twcs.csv.
"""
import pandas as pd, numpy as np, re, sys
from collections import Counter, defaultdict

CSV = r'C:\Users\Siddhi\Desktop\Hiver\twcs\twcs.csv'
BRANDS = ['XboxSupport', 'SpotifyCares']

print("Loading CSV...", flush=True)
df = pd.read_csv(CSV,
    dtype={'tweet_id':'Int64','in_response_to_tweet_id':'float64',
           'author_id':str,'text':str,'inbound':bool},
    usecols=['tweet_id','author_id','inbound','created_at',
             'text','response_tweet_id','in_response_to_tweet_id'])
print(f"Loaded {len(df):,} rows", flush=True)

# ── build child map once ──────────────────────────────────────────
child_map = defaultdict(list)
id2row = {}
for _, row in df.iterrows():
    tid = row['tweet_id']
    if pd.notna(tid):
        id2row[int(tid)] = row
    p = row['in_response_to_tweet_id']
    if pd.notna(p) and pd.notna(tid):
        child_map[int(p)].append(int(tid))

def get_thread(root, max_turns=20):
    visited, q, result = set(), [root], []
    while q and len(result) < max_turns:
        n = q.pop(0)
        if n in visited: continue
        visited.add(n); result.append(n)
        q.extend(child_map.get(n, []))
    return result

# ── response classifiers ──────────────────────────────────────────
DM   = re.compile(r'\bDM\b|direct\s*message|send\s+us\s+a\s+(msg|message)|message\s+us', re.I)
TMPL = re.compile(r"sorry to hear|we apologize|we'?re sorry|apologies for|"
                  r"thank(s| you) for (reaching|contacting)", re.I)
TRBL = re.compile(r'\b(try|restart|reboot|reset|clear\s*cache|reinstall|'
                  r'uninstall|re-?install|update|check|verify|enable|disable|'
                  r'toggle|go\s+to|sign\s+out|log\s+out|navigate|steps|follow)\b', re.I)
LINK = re.compile(r'https?://|bit\.ly|support\.|help\.', re.I)
POLC = re.compile(r'\b(policy|refund|eligible|within\s+\d+\s*day|'
                  r'compensation|submit|claim|appeal)\b', re.I)

def classify(text):
    if DM.search(text):   return 'dm'
    if TRBL.search(text): return 'trouble'
    if LINK.search(text): return 'link'
    if POLC.search(text): return 'policy'
    if TMPL.search(text) and len(text) < 150: return 'template'
    if '?' in text:       return 'clarify'
    return 'other'

SEP = "="*68
results = {}

for BRAND in BRANDS:
    print(f"\n{SEP}\n  {BRAND}\n{SEP}", flush=True)

    out_df = df[df['author_id'] == BRAND]
    n_out  = len(out_df)

    replied_ids = set(out_df['in_response_to_tweet_id'].dropna().astype(int))
    in_df  = df[df['tweet_id'].isin(replied_ids) & df['inbound']]
    n_in   = len(in_df)
    n_custs = in_df['author_id'].nunique()

    print(f"Outbound tweets        : {n_out:,}")
    print(f"Paired inbound         : {n_in:,}")
    print(f"Unique customers       : {n_custs:,}", flush=True)

    # date range
    dates = pd.to_datetime(out_df['created_at'], errors='coerce', utc=True).dropna()
    if len(dates):
        print(f"Date range             : {dates.min().date()} → {dates.max().date()}")

    # ── reconstruct conversations ─────────────────────────────────
    print("Reconstructing conversations...", flush=True)
    roots = set()
    for pid in replied_ids:
        node = pid
        for _ in range(15):
            if node not in id2row: break
            p = id2row[node]['in_response_to_tweet_id']
            if pd.isna(p): break
            node = int(p)
        roots.add(node)

    threads = []
    for root in roots:
        tids = get_thread(root)
        rows = [{'author': id2row[t]['author_id'],
                 'text': str(id2row[t]['text']) if pd.notna(id2row[t]['text']) else ''}
                for t in tids if t in id2row]
        if any(r['author'] == BRAND for r in rows) and len(rows) >= 2:
            threads.append(rows)

    lengths = [len(t) for t in threads]
    n_multi = sum(1 for l in lengths if l >= 3)
    n_long  = sum(1 for l in lengths if l >= 5)
    print(f"Reconstructed convos   : {len(threads):,}")
    print(f"Avg turns              : {np.mean(lengths):.2f}" if lengths else "Avg turns: N/A")
    print(f"3+ turn convos         : {n_multi:,} ({100*n_multi/max(len(threads),1):.1f}%)")
    print(f"5+ turn convos         : {n_long:,}  ({100*n_long/max(len(threads),1):.1f}%)")

    # turn distribution
    dist = Counter(lengths)
    print("Turn dist: " + "  ".join(f"{k}t:{v}" for k,v in sorted(dist.items())[:8]))

    # ── classify brand responses ──────────────────────────────────
    brand_resps = [t['text'] for th in threads for t in th
                   if t['author'] == BRAND and t['text'].strip()]
    cats = Counter(classify(r) for r in brand_resps)
    total_r = max(len(brand_resps), 1)
    print(f"\nResponse quality ({total_r:,} responses):")
    for c,n in sorted(cats.items(), key=lambda x:-x[1]):
        bar = 'X'*min(int(n/total_r*30),30)
        print(f"  {c:<12} {n:>5,} ({100*n/total_r:5.1f}%)  {bar}")
    useful = cats['trouble'] + cats['link'] + cats['policy'] + cats['clarify']
    low    = cats['dm'] + cats['template'] + cats['other']
    print(f"  → Useful for RAG     : {useful:,} ({100*useful/total_r:.1f}%)")
    print(f"  → Low-info/DM        : {low:,}  ({100*low/total_r:.1f}%)")
    print(f"  → DM-redirect rate   : {cats['dm']:,} ({100*cats['dm']/total_r:.1f}%)")

    # ── sample conversations ──────────────────────────────────────
    print(f"\n--- 2 Sample Conversations ---")
    by_len = sorted(threads, key=len)
    picks = [by_len[len(by_len)//3], by_len[min(-1, -len(by_len)//6)]]
    for i, th in enumerate(picks):
        print(f"  [Sample {i+1} — {len(th)} turns]")
        for t in th[:6]:
            role = "BRAND   " if t['author']==BRAND else "CUSTOMER"
            print(f"    [{role}] {t['text'][:160].replace(chr(10),' ')!r}")

    # ── intent discovery ──────────────────────────────────────────
    cust_msgs = [t['text'] for th in threads for t in th
                 if t['author'] != BRAND and t['text'].strip()]
    print(f"\n--- Intent Discovery ({len(cust_msgs):,} customer messages) ---")

    if BRAND == 'XboxSupport':
        intents = {
            'Error Code':            r'\b(0x[0-9A-Fa-f]{4,}|E\d{3,4})\b',
            'Account/Ban/Suspend':   r'\b(account|suspend|ban+ed?|suspended|lock|locked|cannot.access)\b',
            'Download/Install':      r'\b(download|install|patch|update|stuck.at|slow.download)\b',
            'Billing/Subscription':  r'\b(charge|charg|billing|refund|subscri|payment|gold|game.?pass|xbox.live)\b',
            'Network/Multiplayer':   r'\b(connect|online|network|nat|multiplayer|party|lag|disconnect)\b',
            'Content/DLC/Achievement':r'\b(achievement|dlc|content|missing|season.pass|map.pack|not.show)\b',
            'Console/Hardware':      r'\b(console|hardware|disc|disk|controller|broken|repair|wont.turn)\b',
            'Crash/Freeze':          r'\b(crash|freeze|frozen|not.launch|wont.start|performance)\b',
            'Refund':                r'\b(refund|money.back|want.my.money)\b',
        }
    else:
        intents = {
            'Playback Error':        r'\b(play|playing|song|music|skip|pause|stuck|wont.play|not.playing|buffer|stream)\b',
            'Account/Login':         r'\b(log.?in|login|password|account|sign.?in|cant.access|locked.out|forgot)\b',
            'Premium/Subscription':  r'\b(premium|subscri|plan|upgrade|free|cancel|renew)\b',
            'Billing/Charge':        r'\b(charg|bill|payment|refund|invoice|price|cost|paid|fee)\b',
            'App Crash/Bug':         r'\b(crash|freeze|not.work|wont.open|bug|broken|error)\b',
            'Device/Platform':       r'\b(android|ios|iphone|ipad|windows|mac|linux|car|chromecast|ps[34]|tv|alexa|speaker)\b',
            'Playlist/Library':      r'\b(playlist|library|saved|album|miss|disappear|deleted|gone|sync)\b',
            'Content Unavailable':   r'\b(available|region|country|not.available|removed|missing|taken.down|cant.find)\b',
            'Offline/Download':      r'\b(offline|download|downloaded|saved.song)\b',
        }

    intent_counts = {}
    for name, pat in intents.items():
        n = sum(1 for m in cust_msgs if re.search(pat, m, re.I))
        intent_counts[name] = n
    max_ic = max(intent_counts.values()) if intent_counts else 1
    for name, n in sorted(intent_counts.items(), key=lambda x:-x[1]):
        bar = 'X'*min(int(n/max_ic*25),25)
        pct = 100*n/max(len(cust_msgs),1)
        print(f"  {name:<30} {n:>5,} ({pct:5.1f}%)  {bar}")

    # ── error code analysis (Xbox only) ──────────────────────────
    ec_count = 0
    if BRAND == 'XboxSupport':
        print("\n--- Error Code Deep Dive ---")
        ec_pat = re.compile(r'\b(0x[0-9A-Fa-f]{4,}|E\d{3,4})\b')
        ec_msgs = [(m, ec_pat.findall(m)) for m in cust_msgs if ec_pat.search(m)]
        ec_count = len(ec_msgs)
        all_codes = [c for _,codes in ec_msgs for c in codes]
        print(f"  Messages with error codes  : {ec_count:,} ({100*ec_count/max(len(cust_msgs),1):.2f}%)")
        print(f"  Unique codes               : {len(set(all_codes)):,}")
        if all_codes:
            print("  Top codes: " + str(Counter(all_codes).most_common(8)))
        for msg, codes in ec_msgs[:3]:
            print(f"  [{codes}] {msg[:130]!r}")

    # ── platform diversity (Spotify) ─────────────────────────────
    if BRAND == 'SpotifyCares':
        print("\n--- Platform Diversity ---")
        platforms = {'Android':r'\bandroid\b','iOS':r'\b(ios|iphone|ipad)\b',
                     'Windows':r'\bwindows\b','Mac':r'\b(mac|macos)\b',
                     'Speaker':r'\b(alexa|sonos|google.home)\b',
                     'TV/Cast':r'\b(tv|chromecast|firetv)\b','Car':r'\bcar\b'}
        for plat, pat in platforms.items():
            n = sum(1 for m in cust_msgs if re.search(pat, m, re.I))
            print(f"  {plat:<15} {n:>4,} ({100*n/max(len(cust_msgs),1):.1f}%)")

    # ── escalation signals ────────────────────────────────────────
    print("\n--- Escalation Signals ---")
    esc = {
        'Security/hack':     r'\b(hack|hacked|compromis|unauthor|stolen|fraud|secur)\b',
        'Billing dispute':   r'\b(unauthorized.charge|chargeback|wrong.charge|overcharg|dispute)\b',
        'Account locked/ban':r'\b(account.*(lock|ban|suspend)|banned|cannot.access)\b',
        'Urgency':           r'\b(urgent|asap|right.now|immediately|help.me.now)\b',
        'Threat/legal':      r'\b(lawyer|legal|sue|cancel.everything|never.again)\b',
    }
    for sig, pat in esc.items():
        n = sum(1 for m in cust_msgs if re.search(pat, m, re.I))
        print(f"  {sig:<25} {n:>5,} ({100*n/max(len(cust_msgs),1):.1f}%)")

    # ── golden set feasibility ────────────────────────────────────
    useful_ths = [th for th in threads
                  if any(TRBL.search(t['text']) or LINK.search(t['text'])
                         for t in th if t['author']==BRAND)]
    retrieval_pairs = sum(
        1 for th in threads
        for i in range(len(th)-1)
        if th[i]['author']!=BRAND and th[i+1]['author']==BRAND
        and (TRBL.search(th[i+1]['text']) or LINK.search(th[i+1]['text']))
    )
    print(f"\n--- Golden Set & Retrieval ---")
    print(f"  Useful threads (have resolution)  : {len(useful_ths):,}")
    print(f"  Retrieval (Q,A) pairs             : {retrieval_pairs:,}")
    print(f"  Golden set feasible (need ≥400)?  : {'✓ YES' if len(useful_ths)>=400 else '✗ MARGINAL'}")

    results[BRAND] = dict(
        n_out=n_out, n_in=n_in, n_custs=n_custs,
        n_threads=len(threads), avg_len=float(np.mean(lengths)) if lengths else 0,
        n_multi=n_multi, n_long=n_long,
        useful_pct=100*useful/total_r, dm_pct=100*cats['dm']/total_r,
        useful_threads=len(useful_ths), retrieval_pairs=retrieval_pairs,
        error_codes=ec_count,
        top_intents=sorted(intent_counts.items(), key=lambda x:-x[1])[:3],
    )

# ── FINAL COMPARISON ─────────────────────────────────────────────
print(f"\n{SEP}\n  FINAL HEAD-TO-HEAD COMPARISON\n{SEP}")
xb = results['XboxSupport']
sp = results['SpotifyCares']

rows = [
    ("Outbound tweets",          xb['n_out'],          sp['n_out']),
    ("Paired inbound",           xb['n_in'],           sp['n_in']),
    ("Reconstructed convos",     xb['n_threads'],      sp['n_threads']),
    ("Multi-turn (3+)",          xb['n_multi'],        sp['n_multi']),
    ("5+ turn convos",           xb['n_long'],         sp['n_long']),
    ("Avg conv length",          round(xb['avg_len'],2), round(sp['avg_len'],2)),
    ("Useful response %",        round(xb['useful_pct'],1), round(sp['useful_pct'],1)),
    ("DM-redirect %",            round(xb['dm_pct'],1), round(sp['dm_pct'],1)),
    ("Useful threads",           xb['useful_threads'], sp['useful_threads']),
    ("Retrieval pairs",          xb['retrieval_pairs'],sp['retrieval_pairs']),
    ("Error codes in data",      xb['error_codes'],    'N/A'),
]

print(f"  {'Metric':<30} {'XboxSupport':>12}  {'SpotifyCares':>12}  Winner")
print(f"  {'-'*30} {'-'*12}  {'-'*12}  {'-'*12}")
xbox_wins = 0; spot_wins = 0
for metric, xv, sv in rows:
    if isinstance(xv, (int,float)) and isinstance(sv, (int,float)):
        # For DM%, lower is better
        if 'DM' in metric:
            w = 'Xbox' if xv < sv else ('Spotify' if sv < xv else 'Tie')
        else:
            w = 'Xbox' if xv > sv else ('Spotify' if sv > xv else 'Tie')
        if w == 'Xbox': xbox_wins += 1
        elif w == 'Spotify': spot_wins += 1
    else:
        w = '—'
    print(f"  {metric:<30} {str(xv):>12}  {str(sv):>12}  {w}")

print(f"\n  Xbox wins: {xbox_wins}  |  Spotify wins: {spot_wins}")

print(f"""
  Top Xbox intents  : {xb['top_intents']}
  Top Spotify intents: {sp['top_intents']}
""")

# ── DECISION ─────────────────────────────────────────────────────
print(f"{SEP}\n  DATA-DRIVEN DECISION\n{SEP}")

# Score on 5 key criteria (each 0-10)
def ratio_score(a, b): return round(10*a/max(a,b,1), 1)

scores = {
    'XboxSupport':  0.0,
    'SpotifyCares': 0.0,
}

criteria_weighted = [
    # (xbox_val, spot_val, weight, criterion, higher_is_better)
    (xb['n_threads'],       sp['n_threads'],       2.0, "Conversations",       True),
    (xb['useful_pct'],      sp['useful_pct'],       3.0, "Useful response %",   True),
    (100-xb['dm_pct'],      100-sp['dm_pct'],       2.5, "Non-DM rate",         True),
    (xb['retrieval_pairs'], sp['retrieval_pairs'],  2.5, "Retrieval pairs",     True),
    (xb['useful_threads'],  sp['useful_threads'],   2.0, "Useful threads",      True),
    (xb['n_multi'],         sp['n_multi'],          1.5, "Multi-turn convos",   True),
]

print(f"  {'Criterion':<25} {'Xbox':>8} {'Spotify':>8}  {'Weight':>6}")
for xv, sv, w, crit, hib in criteria_weighted:
    mx = max(xv, sv, 1)
    xs = round(10*xv/mx, 1)
    ss = round(10*sv/mx, 1)
    scores['XboxSupport']  += xs * w
    scores['SpotifyCares'] += ss * w
    print(f"  {crit:<25} {xs:>8.1f} {ss:>8.1f}  {w:>6.1f}x")

# qualitative additions
qual = [
    (7, 9, 1.5, "India/global familiarity"),
    (7, 9, 1.0, "Daily use relevance"),
    (8, 8, 1.0, "Intent separability"),
    (8, 7, 1.5, "Technical uniqueness"),
    (8, 4, 2.0, "Anti-cloning/distinctiveness"),
    (8, 9, 1.0, "Implementation speed"),
]
print(f"  --- Qualitative ---")
for xv, sv, w, crit in qual:
    scores['XboxSupport']  += xv * w
    scores['SpotifyCares'] += sv * w
    print(f"  {crit:<25} {xv:>8} {sv:>8}  {w:>6.1f}x")

print(f"\n  {'TOTAL SCORE':<25} {scores['XboxSupport']:>8.2f} {scores['SpotifyCares']:>8.2f}")
WINNER = max(scores, key=scores.get)
margin = abs(scores['XboxSupport'] - scores['SpotifyCares'])
print(f"\n  XXXX WINNER: {WINNER}  (margin={margin:.2f}) XXXX")

# Error code verdict for Xbox
if xb['error_codes'] > 0:
    ec_pct = 100*xb['error_codes']/max(xb['n_in'],1)
    if ec_pct >= 5:
        print(f"\n  Error code signal: STRONG ({xb['error_codes']:,} msgs = {ec_pct:.1f}%) → justifies hybrid retrieval")
    elif ec_pct >= 2:
        print(f"\n  Error code signal: MODERATE ({xb['error_codes']:,} = {ec_pct:.1f}%) → useful but not dominant angle")
    else:
        print(f"\n  Error code signal: WEAK ({xb['error_codes']:,} = {ec_pct:.1f}%) → does NOT justify special architecture")

print(f"\n  ► LOCKED BRAND: {WINNER}")
print(f"  ► Proceed immediately to implementation.")
print(f"\n{'='*68}")

# write result to file so next script can read it
with open(r'C:\Users\Siddhi\Desktop\Hiver\brand_decision.txt', 'w') as f:
    f.write(WINNER)
print(f"Brand decision saved to brand_decision.txt")

