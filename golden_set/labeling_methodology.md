# Golden Set Labelling Methodology

## Status: AWAITING HUMAN REVIEW

The current `golden_set.jsonl` contains 200 examples with **automatically generated labels**.
These are NOT yet hand-labelled. Human review using `human_review.csv` is required before
this set can be described as a hand-labelled golden evaluation set.

---

## How Examples Were Sampled

### Source
All 200 examples come exclusively from `data/processed/test.jsonl` — the **held-out test split**.

No example overlaps with `data/processed/train.jsonl`, `data/processed/val.jsonl`, or the
retrieval corpus (`data/processed/retrieval_corpus.jsonl`).

**Leakage check result: 0 overlapping conversation IDs.** (Verified by `build_golden.py` and
confirmed by `golden_set_audit.py`.)

### Temporal Split
The test split contains conversations from **2017-11-25 to 2017-12-03** — the latest
~20% of the dataset by date. The retrieval corpus uses the earlier 80%.

This temporal split prevents leakage: the agent cannot "remember" a golden example
because it was in the retrieval corpus.

### Sampling Strategy
The 200 examples were sampled using **stratified sampling proportional to the
training-set intent frequency**, with deliberate over-sampling of hard cases:

- ~60% of each intent's quota: easy examples (keyword clearly present, no escalation signal)
- ~25%: hard examples (escalation signals, low-confidence keyword match, or borderline cases)
- ~15%: examples with explicit escalation signals (billing disputes, account security, urgency)

Intent target sizes (proportional to training frequency):

| Intent | Target | Sampled |
|---|---|---|
| playback_error | 38 | 38 |
| device_platform | 33 | 33 |
| premium_subscription | 30 | 30 |
| playlist_library | 26 | 26 |
| billing_charge | 25 | 25 |
| account_login | 16 | 16 |
| offline_download | 13 | 13 |
| content_unavailable | 11 | 11 |
| app_crash_bug | 8 | 8 |
| **Total** | **200** | **200** |

---

## How Current Labels Were Generated (AUTO LABELS — NOT HAND-LABELLED)

### Intent Labels

Intent labels were assigned by a **keyword/regex priority rule system** identical to the one
used for the intent taxonomy. The rules fire in a fixed priority order:

1. `billing_charge` — keywords: charge, charged, bill, payment, refund, invoice, price, cost, paid, fee, money, credit card, debit
2. `account_login` — keywords: login, log in, sign in, password, forgot, locked out, cant access, verify, username, reset pass
3. `premium_subscription` — keywords: premium, subscri, free trial, upgrade, student plan, family plan, duo plan
4. `app_crash_bug` — keywords: crash, freeze, frozen, not working, wont open, bug, broken, glitch, keeps closing, black screen, error
5. `offline_download` — keywords: offline, download, downloaded, saved songs, listen offline, cache
6. `content_unavailable` — keywords: not available, unavailable, region, country, removed, taken down, cant find, no longer, explicit
7. `playlist_library` — keywords: playlist, library, saved, liked songs, songs gone, disappeared, deleted, missing song, sync, my music
8. `device_platform` — keywords: android, ios, iphone, ipad, windows, mac, chromecast, alexa, echo, sonos, speaker, tv, ps3, ps4, car, carplay, roku
9. `playback_error` — keywords: play, playing, song, music, skip, pause, stuck, buffering, stream, wont play, not playing, keeps stopping

The first matching intent in priority order is assigned. If no keyword matches, the example
was excluded from the golden set (not included at all).

**Limitation:** This method will misclassify examples where:
- Multiple intent keywords appear in the same message
- The customer's phrasing does not use the expected keywords
- The message is very short or ambiguous

### Escalation Labels

Escalation labels (`ESCALATE` / `AUTO_HANDLE`) were assigned by a **two-rule heuristic**:
1. Message contains any of: hack, hacked, unauthorised, stolen, fraud, chargeback, dispute,
   wrong charge, overcharged, charged twice, legal, lawyer, sue → `ESCALATE`
2. Intent is `billing_charge` or `account_login` AND no matching keyword resolution was found → `ESCALATE`
3. Otherwise → `AUTO_HANDLE`

Result: 30 ESCALATE (15%) / 170 AUTO_HANDLE (85%).

**Limitation:** This escalation rule does not capture all genuinely risky cases. Some billing
queries that should be escalated may be labelled AUTO_HANDLE if they lack the explicit keywords.

---

## What Reviewers Must Do

Open `human_review.csv` in a spreadsheet application.

For each of the 200 rows:

### Column: `human_intent`

Set to one of these exact strings:

```
playback_error
account_login
premium_subscription
billing_charge
app_crash_bug
playlist_library
content_unavailable
device_platform
offline_download
ambiguous
```

Use `ambiguous` only if the message could genuinely be classified into 2+ intents
with equal justification. Do NOT use it to avoid a decision.

If `auto_intent` looks correct, you may simply copy it. Do not assume it is correct —
check the message yourself.

### Column: `human_escalation`

Set to exactly `ESCALATE` or `AUTO_HANDLE` based on this policy:

**ESCALATE when:**
- The message contains an account security or compromise signal (hacked, stolen, unauthorised)
- The message is a billing dispute (charged incorrectly, refund demand, chargeback)
- The message contains a legal or regulatory threat
- The message cannot be resolved without accessing account data privately
- You are genuinely uncertain whether auto-handling would be safe

**AUTO_HANDLE when:**
- The issue is a standard technical problem (playback, crash, device, playlist)
- A troubleshooting step or self-service link can plausibly resolve it
- No account security or financial risk is evident

When in doubt, escalate. A false escalation is safer than a missed one.

### Column: `reviewer_notes`

Optional. Add notes about edge cases, ambiguities, or errors in the auto-label.

### Flagged Examples (`confidence_note` column)

57 examples are pre-flagged for careful review:
- `SHORT — verify intent`: message is very short and may be ambiguous
- `MULTI-KEYWORD — possible ambiguity`: multiple intent keywords present
- `ESCALATION-SIGNAL — verify label`: keyword-based escalation signal present

These 57 examples deserve extra attention. The remaining 143 are cleaner but should
still be reviewed, not assumed correct.

---

## Intent Definitions for Reviewers

| Intent | What it covers |
|---|---|
| `playback_error` | Song/music won't play, buffering, skipping, pausing unexpectedly, stream issues |
| `account_login` | Cannot log in, password reset issues, account locked/inaccessible |
| `premium_subscription` | Premium plan status, cancellation, trial, plan type questions |
| `billing_charge` | Unexpected charges, payment failures, refund requests, price disputes |
| `app_crash_bug` | App crashes, freezes, black screen, won't open, general app bugs |
| `playlist_library` | Playlists or saved songs missing, deleted, or not syncing |
| `content_unavailable` | Song/album/artist not available — due to region, removal, or licensing |
| `device_platform` | Spotify not working on a specific device (speaker, TV, console, car, browser) |
| `offline_download` | Downloaded songs not playing offline, download failures |

---

## Files

| File | Description |
|---|---|
| `golden_set.jsonl` | Machine-labelled golden set (200 examples, JSONL format) |
| `golden_set.csv` | Same, CSV format |
| `human_review.csv` | Human review spreadsheet — fill `human_intent` and `human_escalation` columns |
| `labeling_methodology.md` | This document |

---

## After Human Review

Once `human_review.csv` is filled:

1. Run a script to merge `human_intent` and `human_escalation` back into `golden_set.jsonl`
2. Compute agreement between `auto_intent` and `human_intent` (as a quality check)
3. Update README and results to clearly state labels are human-verified
4. Re-run evaluation (`evaluate.py`) with the updated labels

Until then, all evaluation results use keyword-derived labels and should be interpreted
with that caveat explicitly stated.
