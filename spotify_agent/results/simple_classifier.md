# Simple Classifier — TF-IDF + Logistic Regression

**Model:** TfidfVectorizer (ngram 1-2, max 30k features) + LogisticRegression (class_weight=balanced)  
**Trained on:** 13,144 examples from train.jsonl  
**Evaluated on:** 200 golden-set examples  

## Validation results

| Metric | Score |
|---|---|
| Accuracy | 0.8963 |
| Macro F1 | 0.8874 |
| Weighted F1 | 0.8966 |

## Golden-set results

| Metric | Score |
|---|---|
| Accuracy | 0.9050 |
| Macro F1 | 0.8925 |
| Weighted F1 | 0.9044 |

## Per-intent F1 (golden set)

| Intent | F1 |
|---|---|
| `billing_charge` | 0.9600 |
| `account_login` | 0.9375 |
| `device_platform` | 0.9375 |
| `offline_download` | 0.9286 |
| `premium_subscription` | 0.8929 |
| `playback_error` | 0.8916 |
| `playlist_library` | 0.8846 |
| `app_crash_bug` | 0.8000 |
| `content_unavailable` | 0.8000 |
