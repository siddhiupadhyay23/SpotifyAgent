"""
Trivial baseline: majority-class predictor.
Predicts every example as the most frequent intent in train.jsonl.
Evaluated on golden_set.jsonl.
"""
import json
from pathlib import Path
from collections import Counter
from sklearn.metrics import accuracy_score, f1_score

TRAIN   = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\train.jsonl")
GOLDEN  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\golden_set\golden_set.jsonl")
RESULTS = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\results")
RESULTS.mkdir(parents=True, exist_ok=True)

import re
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
PRIORITY = ["billing_charge","account_login","premium_subscription","app_crash_bug",
            "offline_download","content_unavailable","playlist_library","device_platform","playback_error"]

def assign_intent(msg):
    matched = [n for n, p in PATTERNS if p.search(msg)]
    if not matched:
        return None
    return next((i for i in PRIORITY if i in matched), matched[0])

# ── 1. Find majority intent from train.jsonl ──────────────────────
train_counts = Counter()
with open(TRAIN, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        intent = assign_intent(r.get("customer_msg",""))
        if intent:
            train_counts[intent] += 1

majority_intent = train_counts.most_common(1)[0][0]
print(f"Majority intent (from train): {majority_intent}  "
      f"(count={train_counts[majority_intent]:,})")

# ── 2. Evaluate on golden set ─────────────────────────────────────
true_labels, pred_labels = [], []
with open(GOLDEN, encoding="utf-8") as f:
    for line in f:
        g = json.loads(line)
        true_labels.append(g["intent"])
        pred_labels.append(majority_intent)   # always predict majority

n = len(true_labels)
acc      = accuracy_score(true_labels, pred_labels)
macro_f1 = f1_score(true_labels, pred_labels, average="macro",  zero_division=0)
wtd_f1   = f1_score(true_labels, pred_labels, average="weighted", zero_division=0)

print(f"Golden examples : {n}")
print(f"Accuracy        : {acc:.4f}")
print(f"Macro F1        : {macro_f1:.4f}")
print(f"Weighted F1     : {wtd_f1:.4f}")

# ── 3. Save ───────────────────────────────────────────────────────
result = {
    "majority_intent": majority_intent,
    "golden_size": n,
    "accuracy":    round(acc,   4),
    "macro_f1":    round(macro_f1, 4),
    "weighted_f1": round(wtd_f1,   4),
    "train_intent_counts": dict(train_counts.most_common()),
}
(RESULTS / "trivial_baseline.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")

md = f"""# Trivial Baseline — Majority-Class Predictor

**Method:** Predict every incoming message as `{majority_intent}`,
the most frequent intent in the training split (count={train_counts[majority_intent]:,}).

**Why this is the right trivial baseline:** A majority-class predictor requires
no understanding of the message. Any useful classifier must beat this.

## Results on golden set (n={n})

| Metric | Score |
|---|---|
| Accuracy | {acc:.4f} |
| Macro F1 | {macro_f1:.4f} |
| Weighted F1 | {wtd_f1:.4f} |

Macro F1 is the headline metric because the golden set is intentionally
imbalanced (mirroring real support volume). A majority predictor scores
near-zero macro F1 because it gets 0 F1 on every non-majority class.
"""
(RESULTS / "trivial_baseline.md").write_text(md, encoding="utf-8")
print(f"Saved -> results/trivial_baseline.json")
print(f"Saved -> results/trivial_baseline.md")
print("DONE. Stopping.")
