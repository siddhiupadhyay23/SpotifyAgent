"""
Simple classifier: TF-IDF + Logistic Regression.
Train on train.jsonl, select on val.jsonl, evaluate on golden_set.jsonl.
"""
import json, re, pickle
from pathlib import Path
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, classification_report

TRAIN   = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\train.jsonl")
VAL     = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\data\processed\val.jsonl")
GOLDEN  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\golden_set\golden_set.jsonl")
RESULTS = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\results")
MODELS  = Path(r"C:\Users\Siddhi\Desktop\Hiver\spotify_agent\models")
RESULTS.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)

INTENTS = ["playback_error","account_login","premium_subscription","billing_charge",
           "app_crash_bug","playlist_library","content_unavailable",
           "device_platform","offline_download"]

# ── Intent labeller (same keyword logic used throughout) ──────────
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

# ── Load split ────────────────────────────────────────────────────
def load_split(path, use_label_field=False):
    """Load (text, label) pairs. Skips examples with no label."""
    texts, labels = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            msg = r.get("customer_msg", "").strip()
            if not msg:
                continue
            if use_label_field:
                label = r.get("intent")          # golden set has explicit label
            else:
                label = assign_intent(msg)       # train/val: derive from keywords
            if label not in INTENTS:
                continue
            texts.append(msg)
            labels.append(label)
    return texts, labels

print("Loading splits ...", flush=True)
X_train, y_train = load_split(TRAIN)
X_val,   y_val   = load_split(VAL)
X_gold,  y_gold  = load_split(GOLDEN, use_label_field=True)

print(f"  Train : {len(X_train):,}  Val : {len(X_val):,}  Golden : {len(X_gold):,}")

# ── Fit TF-IDF ────────────────────────────────────────────────────
print("Fitting TF-IDF ...", flush=True)
vec = TfidfVectorizer(
    ngram_range=(1, 2),
    max_features=30_000,
    sublinear_tf=True,
    min_df=2,
    strip_accents="unicode",
)
Xtr = vec.fit_transform(X_train)
Xvl = vec.transform(X_val)
Xgl = vec.transform(X_gold)
print(f"  Vocab size : {len(vec.vocabulary_):,}")

# ── Train Logistic Regression ─────────────────────────────────────
print("Training LR ...", flush=True)
clf = LogisticRegression(
    max_iter=1000,
    class_weight="balanced",
    solver="lbfgs",
    multi_class="multinomial",
    C=1.0,
    random_state=42,
)
clf.fit(Xtr, y_train)

# ── Validation ────────────────────────────────────────────────────
yv_pred = clf.predict(Xvl)
val_acc  = accuracy_score(y_val, yv_pred)
val_mf1  = f1_score(y_val, yv_pred, average="macro",    labels=INTENTS, zero_division=0)
val_wf1  = f1_score(y_val, yv_pred, average="weighted", labels=INTENTS, zero_division=0)

print("\nValidation:")
print(f"  Accuracy   : {val_acc:.4f}")
print(f"  Macro F1   : {val_mf1:.4f}")
print(f"  Weighted F1: {val_wf1:.4f}")

# ── Golden set evaluation ─────────────────────────────────────────
yg_pred = clf.predict(Xgl)
gold_acc = accuracy_score(y_gold, yg_pred)
gold_mf1 = f1_score(y_gold, yg_pred, average="macro",    labels=INTENTS, zero_division=0)
gold_wf1 = f1_score(y_gold, yg_pred, average="weighted", labels=INTENTS, zero_division=0)

per_intent = f1_score(y_gold, yg_pred, average=None, labels=INTENTS, zero_division=0)
per_intent_dict = {i: round(float(s),4) for i, s in zip(INTENTS, per_intent)}

print("\nGolden:")
print(f"  Accuracy   : {gold_acc:.4f}")
print(f"  Macro F1   : {gold_mf1:.4f}")
print(f"  Weighted F1: {gold_wf1:.4f}")
print("\n  Per-intent F1 (golden):")
for intent, s in sorted(per_intent_dict.items(), key=lambda x: -x[1]):
    n_true = sum(1 for y in y_gold if y == intent)
    print(f"    {intent:<28} {s:.4f}  (n={n_true})")

# ── Save model ────────────────────────────────────────────────────
with open(MODELS / "tfidf_vec.pkl", "wb") as f:
    pickle.dump(vec, f)
with open(MODELS / "lr_clf.pkl", "wb") as f:
    pickle.dump(clf, f)
print("\n  Model saved -> models/tfidf_vec.pkl + models/lr_clf.pkl")

# ── Save results ──────────────────────────────────────────────────
result = {
    "model": "TF-IDF (ngram 1-2, max 30k) + LogisticRegression (balanced)",
    "train_size":   len(X_train),
    "val_size":     len(X_val),
    "golden_size":  len(X_gold),
    "vocab_size":   len(vec.vocabulary_),
    "validation":   {"accuracy": round(val_acc,4), "macro_f1": round(val_mf1,4), "weighted_f1": round(val_wf1,4)},
    "golden":       {"accuracy": round(gold_acc,4), "macro_f1": round(gold_mf1,4), "weighted_f1": round(gold_wf1,4)},
    "per_intent_f1_golden": per_intent_dict,
}
(RESULTS / "simple_classifier.json").write_text(
    json.dumps(result, indent=2), encoding="utf-8")

md_rows = "\n".join(
    f"| `{i}` | {s:.4f} |" for i, s in sorted(per_intent_dict.items(), key=lambda x: -x[1]))
md = f"""# Simple Classifier — TF-IDF + Logistic Regression

**Model:** TfidfVectorizer (ngram 1-2, max 30k features) + LogisticRegression (class_weight=balanced)  
**Trained on:** {len(X_train):,} examples from train.jsonl  
**Evaluated on:** {len(X_gold)} golden-set examples  

## Validation results

| Metric | Score |
|---|---|
| Accuracy | {val_acc:.4f} |
| Macro F1 | {val_mf1:.4f} |
| Weighted F1 | {val_wf1:.4f} |

## Golden-set results

| Metric | Score |
|---|---|
| Accuracy | {gold_acc:.4f} |
| Macro F1 | {gold_mf1:.4f} |
| Weighted F1 | {gold_wf1:.4f} |

## Per-intent F1 (golden set)

| Intent | F1 |
|---|---|
{md_rows}
"""
(RESULTS / "simple_classifier.md").write_text(md, encoding="utf-8")
print("  Saved -> results/simple_classifier.json + .md")
print("DONE. Stopping.")
