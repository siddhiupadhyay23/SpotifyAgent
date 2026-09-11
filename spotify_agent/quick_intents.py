"""Quick intent taxonomy from train.jsonl. No unicode, no heavy deps."""
import json, re
from pathlib import Path
from collections import Counter

TRAIN = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\train.jsonl")
DOCS  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\docs")
DOCS.mkdir(parents=True, exist_ok=True)

msgs = []
with open(TRAIN, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        msgs.append(r.get("customer_msg", ""))

N = len(msgs)
print(f"Messages loaded: {N}")

INTENTS = [
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

counts = Counter()
examples = {}

for msg in msgs:
    matched = [name for name, pat in INTENTS if pat.search(msg)]
    if not matched:
        continue
    assigned = next((i for i in PRIORITY if i in matched), matched[0])
    counts[assigned] += 1
    if assigned not in examples:
        examples[assigned] = msg[:120]

print("\nINTENT COUNTS (from train.jsonl):")
print(f"{'Intent':<28} {'Count':>6}  {'%':>5}")
print("-" * 45)
for name, _ in INTENTS:
    n = counts.get(name, 0)
    print(f"{name:<28} {n:>6}  {100*n/N:>4.1f}%")
print(f"\nUnmatched: {N - sum(counts.values())} ({100*(N-sum(counts.values()))/N:.1f}%)")

# Write markdown
lines = ["# Intent Taxonomy -- SpotifyCares Support Agent\n",
         f"Derived from {N:,} training messages in train.jsonl.\n",
         "Total intents: 9\n"]

DEFS = {
    "playback_error":       "Customer cannot play music: buffering, song skipping, pausing, not starting.",
    "account_login":        "Cannot access account: login failures, forgotten password, locked out.",
    "premium_subscription": "Premium plan questions: status, cancellation, trial, plan type.",
    "billing_charge":       "Unexpected charge, payment failure, refund request.",
    "app_crash_bug":        "App crashes, freezes, black screen, glitch, error.",
    "playlist_library":     "Playlist or saved songs missing, deleted, or not syncing.",
    "content_unavailable":  "Song/album/artist unavailable due to region or removal.",
    "device_platform":      "Spotify not working on a specific device (speaker, TV, phone OS, console).",
    "offline_download":     "Downloaded songs unavailable offline or download failures.",
}

ESC = {
    "playback_error":       "AUTO_HANDLE -- provide troubleshooting steps.",
    "account_login":        "ESCALATE if security/hack signal; AUTO_HANDLE for password reset.",
    "premium_subscription": "AUTO_HANDLE for status queries; ESCALATE if billing dispute.",
    "billing_charge":       "ESCALATE for disputes or unauthorized charges.",
    "app_crash_bug":        "AUTO_HANDLE -- reinstall/update steps.",
    "playlist_library":     "AUTO_HANDLE -- re-login/sync steps; ESCALATE if data loss confirmed.",
    "content_unavailable":  "AUTO_HANDLE -- licensing restrictions cannot be overridden.",
    "device_platform":      "AUTO_HANDLE with device-specific steps.",
    "offline_download":     "AUTO_HANDLE; ESCALATE if premium active but offline fails.",
}

for name, _ in INTENTS:
    n = counts.get(name, 0)
    lines += [
        f"\n## {name}\n",
        f"**Label:** {name.replace('_',' ').title()}  ",
        f"**Training count:** {n:,} ({100*n/N:.1f}%)  ",
        f"**Definition:** {DEFS[name]}  ",
        f"**Escalation policy:** {ESC[name]}  ",
        f"**Example:** `{examples.get(name, 'n/a')}`\n",
    ]

out = DOCS / "intent_taxonomy.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"\nSaved -> {out}")
print("DONE.")
