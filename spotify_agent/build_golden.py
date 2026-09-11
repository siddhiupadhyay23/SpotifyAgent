"""
Task 4: Build 200-example golden set from test.jsonl (held-out split).

Rules:
- Read ONLY test.jsonl (never train or val -- no leakage).
- Assign intent with same priority-keyword logic used for taxonomy.
- Stratify: target counts per intent proportional to training frequency.
- Include hard/escalation examples deliberately.
- Save golden_set/golden_set.jsonl and golden_set/golden_set.csv.
- Print final counts and STOP.
"""
import json, re, random, csv
from pathlib import Path
from collections import defaultdict, Counter

TEST   = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\test.jsonl")
OUTDIR = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\golden_set")
OUTDIR.mkdir(parents=True, exist_ok=True)

SEED = 42
random.seed(SEED)

# ── Load test split ───────────────────────────────────────────────
rows = []
with open(TEST, encoding="utf-8") as f:
    for line in f:
        rows.append(json.loads(line))
print(f"Test rows loaded: {len(rows)}")

# ── Intent patterns (same as taxonomy) ───────────────────────────
PATTERNS = [
    ("playback_error",       re.compile(r"\b(play|playing|song|music|skip|pause|stuck|buffering|stream|wont play|not playing|keeps stopping)\b", re.I)),
    ("account_login",        re.compile(r"\b(login|log in|sign in|password|forgot|locked out|cant access|verify|username|reset pass)\b", re.I)),
    ("premium_subscription", re.compile(r"\b(premium|subscri|free trial|upgrade|student plan|family plan|duo plan|cancel.*plan|plan.*cancel)\b", re.I)),
    ("billing_charge",       re.compile(r"\b(charge|charged|bill|payment|refund|invoice|price|cost|paid|fee|money|credit card|debit)\b", re.I)),
    ("app_crash_bug",        re.compile(r"\b(crash|freeze|frozen|not working|wont open|bug|broken|glitch|keeps closing|black screen|error)\b", re.I)),
    ("playlist_library",     re.compile(r"\b(playlist|library|saved|liked songs|songs gone|disappeared|deleted|missing song|sync|my music)\b", re.I)),
    ("content_unavailable",  re.compile(r"\b(not available|unavailable|region|country|removed|taken down|cant find|no longer|explicit)\b", re.I)),
    ("device_platform",      re.compile(r"\b(android|ios|iphone|ipad|windows|mac|chromecast|alexa|echo|sonos|speaker|tv|ps3|ps4|car|carplay|roku)\b", re.I)),
    ("offline_download",     re.compile(r"\b(offline|download|downloaded|saved songs|listen offline|cache)\b", re.I)),
]

PRIORITY = [
    "billing_charge", "account_login", "premium_subscription",
    "app_crash_bug", "offline_download", "content_unavailable",
    "playlist_library", "device_platform", "playback_error",
]

PLATFORM_PAT = re.compile(
    r"\b(android|ios|iphone|ipad|windows|mac|chromecast|alexa|echo|"
    r"sonos|speaker|tv|ps[34]|car|carplay|roku|web|browser)\b", re.I)

ESCALATION_PAT = re.compile(
    r"\b(hack|hacked|compromis|unauthori[sz]|stolen|fraud|"
    r"chargeback|dispute|wrong charge|overcharg|charged twice|"
    r"account stolen|legal|lawyer|sue|cancel everything)\b", re.I)

HIGH_RISK = {"billing_charge", "account_login"}

def assign_intent(msg):
    matched = [name for name, pat in PATTERNS if pat.search(msg)]
    if not matched:
        return None
    return next((i for i in PRIORITY if i in matched), matched[0])

def extract_platform(msg):
    m = PLATFORM_PAT.search(msg)
    return m.group(0).lower() if m else "unknown"

# ── Label all test rows ───────────────────────────────────────────
labelled = []
for r in rows:
    msg = r.get("customer_msg", "")
    if len(msg.strip()) < 15:
        continue
    intent = assign_intent(msg)
    if intent is None:
        continue
    platform = extract_platform(msg)
    has_esc  = bool(ESCALATION_PAT.search(msg))
    resp     = r.get("brand_response", "")
    has_res  = bool(re.search(
        r"\b(try|restart|reset|clear.?cache|reinstall|update|check|verify|enable|disable|log.?out)\b",
        resp, re.I))
    labelled.append({
        "customer_msg":        msg,
        "brand_response":      resp,
        "intent":              intent,
        "platform":            platform,
        "has_escalation_signal": has_esc,
        "has_resolution":      has_res,
        "response_type":       r.get("response_type", "other"),
        "agent_ts":            r.get("agent_ts", ""),
        "convo_id":            str(r.get("agent_tweet_id", "")),
    })

print(f"Labelled examples in test pool: {len(labelled)}")

intent_dist = Counter(x["intent"] for x in labelled)
print("Test pool intent distribution:")
for name, n in sorted(intent_dist.items(), key=lambda x: -x[1]):
    print(f"  {name:<28} {n:>5}")

# ── Target sizes (200 total, proportional to training frequency) ──
TRAIN_COUNTS = {
    "playback_error":       2478,
    "device_platform":      2160,
    "premium_subscription": 1943,
    "playlist_library":     1712,
    "billing_charge":       1613,
    "account_login":        1077,
    "offline_download":     848,
    "content_unavailable":  699,
    "app_crash_bug":        614,
}
TOTAL_TRAIN = sum(TRAIN_COUNTS.values())
TARGET_TOTAL = 200

targets = {}
for intent, train_n in TRAIN_COUNTS.items():
    raw = round(TARGET_TOTAL * train_n / TOTAL_TRAIN)
    available = intent_dist.get(intent, 0)
    targets[intent] = min(max(raw, 5), available)   # at least 5, cap at available

# Normalise to exactly 200
shortfall = TARGET_TOTAL - sum(targets.values())
if shortfall > 0:
    # add to largest intents first
    for intent in sorted(targets, key=lambda i: -TRAIN_COUNTS.get(i, 0)):
        if shortfall == 0:
            break
        cap = intent_dist.get(intent, 0)
        if targets[intent] < cap:
            targets[intent] += 1
            shortfall -= 1
elif shortfall < 0:
    for intent in sorted(targets, key=lambda i: TRAIN_COUNTS.get(i, 0)):
        if shortfall == 0:
            break
        if targets[intent] > 5:
            targets[intent] -= 1
            shortfall += 1

print(f"\nTarget golden set sizes (sum={sum(targets.values())}):")
for intent, n in sorted(targets.items(), key=lambda x: -x[1]):
    print(f"  {intent:<28} {n:>3}")

# ── Stratified sampling ───────────────────────────────────────────
by_intent = defaultdict(list)
for ex in labelled:
    by_intent[ex["intent"]].append(ex)

# Shuffle each pool
for k in by_intent:
    random.shuffle(by_intent[k])

golden = []
for intent, target_n in targets.items():
    pool = by_intent[intent]
    if not pool:
        print(f"  WARNING: no examples for {intent}")
        continue

    # Split pool into easy / hard / escalation
    hard = [x for x in pool if not x["has_resolution"] or x["has_escalation_signal"]]
    easy = [x for x in pool if x["has_resolution"] and not x["has_escalation_signal"]]
    esc  = [x for x in pool if x["has_escalation_signal"]]

    n_easy = max(1, int(target_n * 0.60))
    n_hard = max(1, int(target_n * 0.25))
    n_esc  = target_n - n_easy - n_hard

    selected = []
    seen_ids = set()

    def add(src, n):
        added = 0
        for item in src:
            cid = item["convo_id"]
            if cid not in seen_ids and added < n:
                seen_ids.add(cid)
                selected.append(item)
                added += 1

    add(easy, n_easy)
    add(hard, n_hard)
    add(esc,  max(n_esc, 0))

    # Top-up if still short
    remaining = target_n - len(selected)
    if remaining > 0:
        extras = [x for x in pool if x["convo_id"] not in seen_ids]
        add(extras, remaining)

    for ex in selected:
        ex["intent"] = intent   # enforce label

    golden.extend(selected)

random.shuffle(golden)

# ── Assign golden IDs and escalation labels ───────────────────────
for i, g in enumerate(golden):
    g["golden_id"] = f"g{i+1:04d}"
    # Escalation: ESCALATE if security/hack keyword OR
    #             (high-risk intent AND weak evidence)
    g["escalation_label"] = (
        "ESCALATE"
        if g["has_escalation_signal"]
        or (g["intent"] in HIGH_RISK and not g["has_resolution"])
        else "AUTO_HANDLE"
    )

# ── Stats ─────────────────────────────────────────────────────────
print(f"\nFinal golden set: {len(golden)} examples")
final_dist = Counter(g["intent"] for g in golden)
esc_count  = sum(1 for g in golden if g["escalation_label"] == "ESCALATE")
plat_dist  = Counter(g["platform"] for g in golden)

print("Intent distribution:")
for intent, n in sorted(final_dist.items(), key=lambda x: -x[1]):
    print(f"  {intent:<28} {n:>3}")
print(f"Escalation labels: {esc_count} ESCALATE / {len(golden)-esc_count} AUTO_HANDLE")
print("Platform distribution:")
for p, n in sorted(plat_dist.items(), key=lambda x: -x[1])[:8]:
    print(f"  {p:<15} {n:>3}")

# ── Save ──────────────────────────────────────────────────────────
jsonl_path = OUTDIR / "golden_set.jsonl"
csv_path   = OUTDIR / "golden_set.csv"

with open(jsonl_path, "w", encoding="utf-8") as f:
    for g in golden:
        f.write(json.dumps(g, ensure_ascii=False) + "\n")

fieldnames = ["golden_id","customer_msg","intent","escalation_label",
              "platform","has_escalation_signal","has_resolution",
              "response_type","brand_response","agent_ts","convo_id"]
with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(golden)

print(f"\nSaved -> {jsonl_path}")
print(f"Saved -> {csv_path}")
print("build_golden DONE.")
