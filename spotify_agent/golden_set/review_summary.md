# Kiro Proposed Labels — Review Summary

**Label source:** `kiro_proposed` — Kiro AI classifier using semantic keyword rules  
**Status:** NOT human-labelled. All labels carry `label_source = kiro_proposed`.  
**Requires human verification before use as ground truth.**

---

## Overview

| Item | Value |
|---|---|
| Total examples | 200 |
| Needs human review | 147 (74%) |
| Disagrees with auto_intent | 27 |
| Disagrees with auto_escalation | 10 |

---

## Proposed Intent Distribution

| Intent | Count | % |
|---|---|---|
| `device_platform` | 34 | 17.0% |
| `billing_charge` | 34 | 17.0% |
| `playback_error` | 29 | 14.5% |
| `playlist_library` | 27 | 13.5% |
| `premium_subscription` | 25 | 12.5% |
| `account_login` | 22 | 11.0% |
| `content_unavailable` | 11 | 5.5% |
| `app_crash_bug` | 9 | 4.5% |
| `offline_download` | 9 | 4.5% |

---

## Proposed Escalation Distribution

| Decision | Count | % |
|---|---|---|
| `AUTO_HANDLE` | 174 | 87.0% |
| `ESCALATE` | 26 | 13.0% |

---

## Ambiguous Cases Needing Human Review (147 examples)

Flagged when: message is short/ambiguous, matches 3+ intents,
contains multi-issue language, or no pattern matched.

| ID | Kiro Intent | Kiro Esc | Reason |
|---|---|---|---|
| g0003 | `account_login` | `AUTO_HANDLE` | multi-issue language ⚠ escalation differs from auto |
| g0004 | `device_platform` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (playback_e ⚠ intent differs from auto |
| g0005 | `app_crash_bug` | `AUTO_HANDLE` | matches 3 intents: ['app_crash_bug', 'offline_download', 'de ⚠ intent differs from auto |
| g0006 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0007 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0009 | `billing_charge` | `AUTO_HANDLE` |  |
| g0010 | `premium_subscription` | `AUTO_HANDLE` | matches 4 intents: ['premium_subscription', 'offline_downloa |
| g0011 | `offline_download` | `AUTO_HANDLE` | matches 3 intents: ['offline_download', 'playlist_library',  |
| g0012 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0015 | `content_unavailable` | `AUTO_HANDLE` | multi-issue language |
| g0016 | `playlist_library` | `AUTO_HANDLE` | multi-issue language; no pattern matched — fallback to auto_ |
| g0017 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0018 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0019 | `billing_charge` | `ESCALATE` | multi-issue language |
| g0020 | `billing_charge` | `AUTO_HANDLE` | multi-issue language |
| g0021 | `billing_charge` | `AUTO_HANDLE` | matches 3 intents: ['billing_charge', 'premium_subscription' ⚠ intent differs from auto |
| g0022 | `app_crash_bug` | `AUTO_HANDLE` | multi-issue language; no pattern matched — fallback to auto_ |
| g0023 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0026 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0027 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0028 | `billing_charge` | `ESCALATE` | multi-issue language ⚠ escalation differs from auto |
| g0029 | `billing_charge` | `AUTO_HANDLE` | multi-issue language |
| g0030 | `premium_subscription` | `AUTO_HANDLE` |  |
| g0031 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0033 | `premium_subscription` | `AUTO_HANDLE` |  |
| g0034 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0035 | `account_login` | `ESCALATE` | matches 3 intents: ['account_login', 'playlist_library', 'pl ⚠ intent differs from auto |
| g0036 | `premium_subscription` | `AUTO_HANDLE` | matches 3 intents: ['premium_subscription', 'device_platform |
| g0037 | `billing_charge` | `AUTO_HANDLE` | multi-issue language ⚠ escalation differs from auto |
| g0038 | `offline_download` | `AUTO_HANDLE` | multi-issue language |
| g0039 | `billing_charge` | `AUTO_HANDLE` |  |
| g0041 | `account_login` | `ESCALATE` | multi-issue language; disagrees with auto_intent (playlist_l ⚠ intent differs from auto |
| g0042 | `account_login` | `ESCALATE` | multi-issue language |
| g0043 | `billing_charge` | `AUTO_HANDLE` |  |
| g0044 | `billing_charge` | `AUTO_HANDLE` | multi-issue language |
| g0045 | `account_login` | `ESCALATE` | multi-issue language; disagrees with auto_intent (device_pla ⚠ intent differs from auto |
| g0046 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0047 | `device_platform` | `AUTO_HANDLE` | short/ambiguous message |
| g0049 | `app_crash_bug` | `AUTO_HANDLE` | multi-issue language |
| g0050 | `account_login` | `ESCALATE` | multi-issue language |
| g0053 | `billing_charge` | `ESCALATE` | multi-issue language ⚠ escalation differs from auto |
| g0054 | `premium_subscription` | `AUTO_HANDLE` | matches 3 intents: ['premium_subscription', 'content_unavail |
| g0056 | `premium_subscription` | `AUTO_HANDLE` | matches 3 intents: ['premium_subscription', 'playlist_librar |
| g0057 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0058 | `offline_download` | `AUTO_HANDLE` | multi-issue language |
| g0063 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0065 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0066 | `billing_charge` | `ESCALATE` | matches 3 intents: ['billing_charge', 'account_login', 'prem |
| g0067 | `account_login` | `AUTO_HANDLE` | multi-issue language |
| g0068 | `billing_charge` | `AUTO_HANDLE` |  |
| g0069 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0071 | `account_login` | `ESCALATE` | multi-issue language |
| g0072 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0073 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0075 | `offline_download` | `AUTO_HANDLE` | short/ambiguous message |
| g0076 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0077 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0078 | `account_login` | `AUTO_HANDLE` | multi-issue language |
| g0079 | `offline_download` | `AUTO_HANDLE` | multi-issue language |
| g0080 | `billing_charge` | `AUTO_HANDLE` | multi-issue language |
| g0081 | `billing_charge` | `AUTO_HANDLE` | matches 4 intents: ['billing_charge', 'playlist_library', 'd ⚠ intent differs from auto |
| g0082 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0083 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0085 | `billing_charge` | `ESCALATE` | matches 3 intents: ['billing_charge', 'account_login', 'play ⚠ intent differs from auto |
| g0086 | `playlist_library` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (device_pla ⚠ intent differs from auto |
| g0087 | `device_platform` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (playback_e ⚠ intent differs from auto |
| g0088 | `content_unavailable` | `AUTO_HANDLE` | multi-issue language |
| g0089 | `content_unavailable` | `AUTO_HANDLE` | multi-issue language |
| g0091 | `content_unavailable` | `AUTO_HANDLE` | matches 3 intents: ['content_unavailable', 'device_platform' |
| g0092 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0093 | `playlist_library` | `AUTO_HANDLE` | matches 3 intents: ['playlist_library', 'device_platform', ' |
| g0095 | `app_crash_bug` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (offline_do ⚠ intent differs from auto |
| g0096 | `app_crash_bug` | `AUTO_HANDLE` | multi-issue language; no pattern matched — fallback to auto_ |
| g0097 | `playlist_library` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (app_crash_ ⚠ intent differs from auto |
| g0101 | `device_platform` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (playlist_l ⚠ intent differs from auto |
| g0102 | `device_platform` | `AUTO_HANDLE` | short/ambiguous message |
| g0103 | `offline_download` | `AUTO_HANDLE` | matches 3 intents: ['offline_download', 'playlist_library',  |
| g0104 | `billing_charge` | `ESCALATE` | multi-issue language |
| g0105 | `device_platform` | `ESCALATE` | multi-issue language |
| g0106 | `premium_subscription` | `AUTO_HANDLE` |  |
| g0108 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0112 | `account_login` | `AUTO_HANDLE` |  ⚠ escalation differs from auto |
| g0113 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0114 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0115 | `content_unavailable` | `AUTO_HANDLE` | multi-issue language |
| g0116 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0117 | `billing_charge` | `AUTO_HANDLE` | multi-issue language |
| g0119 | `account_login` | `ESCALATE` | multi-issue language; disagrees with auto_intent (premium_su ⚠ intent differs from auto |
| g0121 | `content_unavailable` | `AUTO_HANDLE` | multi-issue language |
| g0122 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0123 | `device_platform` | `AUTO_HANDLE` | short/ambiguous message |
| g0127 | `offline_download` | `AUTO_HANDLE` | multi-issue language |
| g0128 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0129 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0130 | `account_login` | `AUTO_HANDLE` | matches 3 intents: ['account_login', 'playlist_library', 'pl |
| g0131 | `account_login` | `AUTO_HANDLE` | multi-issue language |
| g0132 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0133 | `playback_error` | `ESCALATE` | multi-issue language |
| g0135 | `billing_charge` | `ESCALATE` | matches 3 intents: ['billing_charge', 'account_login', 'prem ⚠ intent differs from auto |
| g0136 | `account_login` | `AUTO_HANDLE` |  |
| g0137 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0138 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0139 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0140 | `billing_charge` | `AUTO_HANDLE` | disagrees with auto_intent (playback_error) ⚠ intent differs from auto |
| g0141 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0142 | `premium_subscription` | `AUTO_HANDLE` |  |
| g0143 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0144 | `content_unavailable` | `AUTO_HANDLE` | matches 3 intents: ['content_unavailable', 'playlist_library |
| g0145 | `billing_charge` | `AUTO_HANDLE` | multi-issue language ⚠ escalation differs from auto |
| g0146 | `account_login` | `AUTO_HANDLE` |  |
| g0147 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0149 | `playlist_library` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (offline_do ⚠ intent differs from auto |
| g0150 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0152 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0153 | `playlist_library` | `AUTO_HANDLE` | multi-issue language; disagrees with auto_intent (playback_e ⚠ intent differs from auto |
| g0154 | `account_login` | `ESCALATE` | multi-issue language; disagrees with auto_intent (premium_su ⚠ intent differs from auto |
| g0156 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0157 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0158 | `billing_charge` | `ESCALATE` | multi-issue language; disagrees with auto_intent (premium_su ⚠ intent differs from auto |
| g0159 | `billing_charge` | `AUTO_HANDLE` |  |
| g0160 | `premium_subscription` | `AUTO_HANDLE` | multi-issue language |
| g0162 | `billing_charge` | `AUTO_HANDLE` | disagrees with auto_intent (playlist_library) ⚠ intent differs from auto |
| g0163 | `playlist_library` | `AUTO_HANDLE` | no pattern matched — fallback to auto_intent |
| g0164 | `device_platform` | `AUTO_HANDLE` | multi-issue language |
| g0165 | `account_login` | `AUTO_HANDLE` |  ⚠ escalation differs from auto |
| g0167 | `premium_subscription` | `AUTO_HANDLE` | matches 3 intents: ['premium_subscription', 'content_unavail |
| g0168 | `app_crash_bug` | `AUTO_HANDLE` | matches 3 intents: ['app_crash_bug', 'device_platform', 'pla |
| g0169 | `account_login` | `AUTO_HANDLE` | multi-issue language |
| g0170 | `account_login` | `AUTO_HANDLE` |  |
| g0171 | `account_login` | `AUTO_HANDLE` |  |
| g0172 | `billing_charge` | `AUTO_HANDLE` | matches 3 intents: ['billing_charge', 'premium_subscription' ⚠ intent differs from auto |
| g0174 | `device_platform` | `AUTO_HANDLE` | short/ambiguous message |
| g0177 | `playback_error` | `AUTO_HANDLE` | multi-issue language |
| g0178 | `premium_subscription` | `AUTO_HANDLE` |  |
| g0179 | `billing_charge` | `AUTO_HANDLE` |  |
| g0181 | `offline_download` | `AUTO_HANDLE` | matches 3 intents: ['offline_download', 'playlist_library',  |
| g0184 | `premium_subscription` | `AUTO_HANDLE` |  |
| g0185 | `billing_charge` | `AUTO_HANDLE` |  |
| g0187 | `premium_subscription` | `ESCALATE` | multi-issue language |
| g0188 | `billing_charge` | `AUTO_HANDLE` | multi-issue language ⚠ escalation differs from auto |
| g0190 | `billing_charge` | `AUTO_HANDLE` | multi-issue language ⚠ escalation differs from auto |
| g0192 | `billing_charge` | `AUTO_HANDLE` | matches 4 intents: ['billing_charge', 'premium_subscription' ⚠ intent differs from auto |
| g0193 | `premium_subscription` | `AUTO_HANDLE` | disagrees with auto_intent (playback_error) ⚠ intent differs from auto |
| g0194 | `playlist_library` | `AUTO_HANDLE` | multi-issue language |
| g0195 | `content_unavailable` | `AUTO_HANDLE` | matches 3 intents: ['content_unavailable', 'device_platform' |
| g0196 | `app_crash_bug` | `AUTO_HANDLE` | multi-issue language |
| g0198 | `billing_charge` | `ESCALATE` | multi-issue language |

---

## Disagreements with Auto-Label

Kiro disagrees with the keyword-rule auto_intent on **27 examples**
(13.5%). These are the most important to human-verify.

| ID | Auto Intent | Kiro Intent | Message (first 70 chars) |
|---|---|---|---|
| g0004 | `playback_error` | `device_platform` | @115888 it’s almost 2018.  When will you “allow” an Apple Watch app?   |
| g0005 | `offline_download` | `app_crash_bug` | @SpotifyCares 
"Click to install new update"..... *spotify closes*.... |
| g0021 | `premium_subscription` | `billing_charge` | @SpotifyCares have been using the free version for a while with no pro |
| g0035 | `offline_download` | `account_login` | Someone hacked my Spotify account of 5+ years and replaced all my save |
| g0041 | `playlist_library` | `account_login` | Someone hacked my Spotify and deleted all of my playlists... why would |
| g0045 | `device_platform` | `account_login` | @SpotifyCares foreign speakers are showing up on my list of Available  |
| g0081 | `playlist_library` | `billing_charge` | @115888 I don’t pay every month so you can restrict my music listening |
| g0085 | `playback_error` | `billing_charge` | @SpotifyCares someone has hacked my spotify account. I refuse to pay f |
| g0086 | `device_platform` | `playlist_library` | @SpotifyCares It’s iOS, iPhone 6s. v8.4.28.1104. I’m sure it’s working |
| g0087 | `playback_error` | `device_platform` | @115888 why is it that when I click to watch the ad to get 30 minutes  |
| g0095 | `offline_download` | `app_crash_bug` | @SpotifyCares No it did nothing 😥 I also tried uninstalling, wiping th |
| g0097 | `app_crash_bug` | `playlist_library` | @SpotifyCares I mean, yeah, it usually does. The problem is that I'm t |
| g0099 | `playback_error` | `account_login` | @SpotifyCares I think my account has been hacked, someone keeps playin |
| g0101 | `playlist_library` | `device_platform` | @SpotifyCares iPad mini2, iPhone SE, both iOS 11.1.2 - but this issue  |
| g0107 | `playback_error` | `account_login` | @115888 my Spotify keeps jumping to play Drill Beats. Has my account b |
| g0119 | `premium_subscription` | `account_login` | @SpotifyCares my Spotify premium got hacked — got a notification that  |
| g0135 | `account_login` | `billing_charge` | @SpotifyCares I have the family plan and a hacker has hacked me twice  |
| g0140 | `playback_error` | `billing_charge` | @SpotifyCares I wanted you to know that I don’t pay for music. |
| g0149 | `offline_download` | `playlist_library` | @115888 not that it wasnt my own damn fault but this is the 5th time t |
| g0153 | `playback_error` | `playlist_library` | @SpotifyCares I have my phone but it isn't ideal when listening to mus |
| g0154 | `premium_subscription` | `account_login` | @SpotifyCares hi Spotify you've sent this link in an email to me to co |
| g0158 | `premium_subscription` | `billing_charge` | @115888 can’t pay because my visa was stolen and doesn’t work, having  |
| g0162 | `playlist_library` | `billing_charge` | Ok so that’s twice in the last week my library has deleted itself for  |
| g0172 | `premium_subscription` | `billing_charge` | @115888 App won't load on my Galaxy S8+. Bit naughty considering I pay |
| g0192 | `premium_subscription` | `billing_charge` | @SpotifyCares hey, I pay for spotify premium and every other week, som |
| g0193 | `playback_error` | `premium_subscription` | @SpotifyCares Why is my account suddenly paused  just a few days after |
| g0197 | `playback_error` | `playlist_library` | @SpotifyCares Sorry I meant more if I have music in my collection that |

---

## Methodology

Labels were assigned by Kiro using **semantic keyword patterns** derived from the
intent taxonomy definitions in `docs/intent_taxonomy.md`.

Priority order (highest specificity first):
1. billing_charge
2. account_login
3. premium_subscription
4. app_crash_bug
5. offline_download
6. content_unavailable
7. playlist_library
8. device_platform
9. playback_error (catch-all)

Escalation rules:
- **ESCALATE** if: hack/compromise keywords, billing dispute keywords (refund +
  charge context), legal threats, unauthorized access language
- **AUTO_HANDLE** otherwise

This is more conservative than the original auto_intent labels.
`billing_charge` now escalates more reliably; `account_login` only escalates
on explicit security signals.

---

## Files

| File | Description |
|---|---|
| `human_review.csv` | Original file — UNCHANGED |
| `kiro_proposed_labels.csv` | Kiro proposals for all 200 examples |
| `review_summary.md` | This file |
| `labeling_methodology.md` | Sampling and annotation methodology |
