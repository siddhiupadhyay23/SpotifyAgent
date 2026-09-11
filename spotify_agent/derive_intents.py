"""
Task 3: Derive intent taxonomy from actual training data.
Counts keyword hits across train.jsonl and saves docs/intent_taxonomy.json.
Run: python derive_intents.py
"""
import json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from config import PROC_DIR, DOCS_DIR

DOCS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load training customer messages ──────────────────────────────
print("Loading train.jsonl ...", flush=True)
msgs = []
with open(PROC_DIR / "train.jsonl", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        msgs.append(r.get("customer_msg", ""))
print(f"  {len(msgs):,} training messages")

# ── Intent keyword patterns (data-driven, confirmed by fast_compare) ──
PATTERNS = {
    "playback_error": re.compile(
        r"\b(play|playing|song|music|skip|pause|stuck|won.t play|not playing|"
        r"buffer|stream|audio|sound|no sound|keep.?stop|keep.?paus)\b", re.I),
    "account_login": re.compile(
        r"\b(log.?in|login|sign.?in|password|forgot|reset.?pass|"
        r"can.?t access|locked out|account.*access|verify|username)\b", re.I),
    "premium_subscription": re.compile(
        r"\b(premium|subscri|free trial|upgrade|cancel.*subscri|"
        r"subscri.*cancel|student plan|family plan|duo plan|plan)\b", re.I),
    "billing_charge": re.compile(
        r"\b(charge|charg|bill|payment|refund|invoice|price|cost|paid|fee|"
        r"money|transaction|receipt|credit card|debit)\b", re.I),
    "app_crash_bug": re.compile(
        r"\b(crash|freeze|frozen|not work|won.t open|bug|broken|error|"
        r"glitch|keep.?clos|shut.?down|force.?clos|black screen)\b", re.I),
    "playlist_library": re.compile(
        r"\b(playlist|library|saved|album|song.?gone|disappear|delet|"
        r"missing.*song|sync|liked song|my music|collection)\b", re.I),
    "content_unavailable": re.compile(
        r"\b(not available|unavailable|region|country|remov|taken down|"
        r"can.t find|no longer|artist.*gone|album.*gone|explicit)\b", re.I),
    "device_platform": re.compile(
        r"\b(android|ios|iphone|ipad|windows|mac|linux|car|chromecast|"
        r"ps[34]|playstation|smart.?tv|\btv\b|alexa|echo|sonos|speaker|watch|"
        r"carplay|android.auto|roku|firetv|fire stick)\b", re.I),
    "offline_download": re.compile(
        r"\b(offline|download|downloaded|save.*listen|listen.*offline|"
        r"saved.*song|cache)\b", re.I),
}

# ── Count hits per message (assign to best-matching intent) ──────
intent_counts = Counter()
intent_examples = defaultdict(list)
unmatched = []

for msg in msgs:
    matched = []
    for name, pat in PATTERNS.items():
        if pat.search(msg):
            matched.append(name)
    if not matched:
        unmatched.append(msg)
        continue
    # Assign to the FIRST matching intent in priority order
    PRIORITY = [
        "billing_charge", "account_login", "premium_subscription",
        "app_crash_bug", "offline_download", "content_unavailable",
        "playlist_library", "device_platform", "playback_error",
    ]
    assigned = next((i for i in PRIORITY if i in matched), matched[0])
    intent_counts[assigned] += 1
    if len(intent_examples[assigned]) < 5:
        intent_examples[assigned].append(msg[:200])

total_matched = sum(intent_counts.values())
total = len(msgs)

print(f"\nIntent distribution (from {total:,} training messages):")
print(f"  {'Intent':<30} {'Count':>6}  {'%':>5}  {'Examples'}")
print("  " + "-"*70)
for intent in PRIORITY:
    n   = intent_counts.get(intent, 0)
    pct = 100 * n / total
    ex  = intent_examples.get(intent, ["—"])[0][:60]
    print(f"  {intent:<30} {n:>6,}  {pct:>4.1f}%  {ex!r}")

print(f"\n  Unmatched (no keyword hit) : {len(unmatched):,} "
      f"({100*len(unmatched)/total:.1f}%)")
print(f"  Total matched              : {total_matched:,} "
      f"({100*total_matched/total:.1f}%)")

# ── Save taxonomy ─────────────────────────────────────────────────
taxonomy = {
    "playback_error": {
        "label": "Playback Error",
        "definition": "Customer cannot play music: buffering, song won't start, skipping, pausing unexpectedly.",
        "train_count": intent_counts.get("playback_error", 0),
        "train_pct": round(100 * intent_counts.get("playback_error", 0) / total, 2),
        "examples": intent_examples.get("playback_error", [])[:3],
        "nearest_confusable": "app_crash_bug",
        "escalation": "AUTO_HANDLE — troubleshoot first; ESCALATE only if persists >24h",
    },
    "account_login": {
        "label": "Account / Login",
        "definition": "Cannot access account: login failures, password reset, locked account.",
        "train_count": intent_counts.get("account_login", 0),
        "train_pct": round(100 * intent_counts.get("account_login", 0) / total, 2),
        "examples": intent_examples.get("account_login", [])[:3],
        "nearest_confusable": "premium_subscription",
        "escalation": "ESCALATE if hack/security signal; AUTO_HANDLE for password reset",
    },
    "premium_subscription": {
        "label": "Premium / Subscription",
        "definition": "Questions about premium plan status, cancellation, trials, plan types.",
        "train_count": intent_counts.get("premium_subscription", 0),
        "train_pct": round(100 * intent_counts.get("premium_subscription", 0) / total, 2),
        "examples": intent_examples.get("premium_subscription", [])[:3],
        "nearest_confusable": "billing_charge",
        "escalation": "AUTO_HANDLE for status queries; ESCALATE if charge dispute",
    },
    "billing_charge": {
        "label": "Billing / Charge",
        "definition": "Unexpected charges, payment failures, refund requests.",
        "train_count": intent_counts.get("billing_charge", 0),
        "train_pct": round(100 * intent_counts.get("billing_charge", 0) / total, 2),
        "examples": intent_examples.get("billing_charge", [])[:3],
        "nearest_confusable": "premium_subscription",
        "escalation": "ESCALATE for disputes / unauthorized charges",
    },
    "app_crash_bug": {
        "label": "App Crash / Bug",
        "definition": "App crashes, freezes, won't open, black screen.",
        "train_count": intent_counts.get("app_crash_bug", 0),
        "train_pct": round(100 * intent_counts.get("app_crash_bug", 0) / total, 2),
        "examples": intent_examples.get("app_crash_bug", [])[:3],
        "nearest_confusable": "playback_error",
        "escalation": "AUTO_HANDLE with reinstall/update steps",
    },
    "playlist_library": {
        "label": "Playlist / Library",
        "definition": "Playlists or saved songs missing, deleted, or not syncing.",
        "train_count": intent_counts.get("playlist_library", 0),
        "train_pct": round(100 * intent_counts.get("playlist_library", 0) / total, 2),
        "examples": intent_examples.get("playlist_library", [])[:3],
        "nearest_confusable": "account_login",
        "escalation": "AUTO_HANDLE with re-login/sync; ESCALATE if confirmed data loss",
    },
    "content_unavailable": {
        "label": "Content Unavailable",
        "definition": "Songs/albums/artists unavailable: regional restrictions, content removal.",
        "train_count": intent_counts.get("content_unavailable", 0),
        "train_pct": round(100 * intent_counts.get("content_unavailable", 0) / total, 2),
        "examples": intent_examples.get("content_unavailable", [])[:3],
        "nearest_confusable": "playlist_library",
        "escalation": "AUTO_HANDLE — licensing restrictions cannot be overridden",
    },
    "device_platform": {
        "label": "Device / Platform",
        "definition": "Spotify not working on a specific device: speaker, TV, console, car.",
        "train_count": intent_counts.get("device_platform", 0),
        "train_pct": round(100 * intent_counts.get("device_platform", 0) / total, 2),
        "examples": intent_examples.get("device_platform", [])[:3],
        "nearest_confusable": "app_crash_bug",
        "escalation": "AUTO_HANDLE with device-specific troubleshooting",
    },
    "offline_download": {
        "label": "Offline / Download",
        "definition": "Downloaded songs not available offline, download failures.",
        "train_count": intent_counts.get("offline_download", 0),
        "train_pct": round(100 * intent_counts.get("offline_download", 0) / total, 2),
        "examples": intent_examples.get("offline_download", [])[:3],
        "nearest_confusable": "playback_error",
        "escalation": "AUTO_HANDLE; ESCALATE if premium active but offline fails",
    },
}

out = DOCS_DIR / "intent_taxonomy.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(taxonomy, f, indent=2, ensure_ascii=False)
print(f"\nSaved intent taxonomy -> {out}")
print("derive_intents complete.")
