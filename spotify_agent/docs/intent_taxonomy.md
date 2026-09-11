# Intent Taxonomy -- SpotifyCares Support Agent

Derived from 28,594 training messages in train.jsonl.

Total intents: 9


## playback_error

**Label:** Playback Error  
**Training count:** 2,478 (8.7%)  
**Definition:** Customer cannot play music: buffering, song skipping, pausing, not starting.  
**Escalation policy:** AUTO_HANDLE -- provide troubleshooting steps.  
**Example:** `@SpotifyCares Feature suggestion: ability to stream to @44842 from the PC app.`


## account_login

**Label:** Account Login  
**Training count:** 1,077 (3.8%)  
**Definition:** Cannot access account: login failures, forgotten password, locked out.  
**Escalation policy:** ESCALATE if security/hack signal; AUTO_HANDLE for password reset.  
**Example:** `@SpotifyCares Y'all having a server error? I can't use the browser version right now. Keeps redirecting me to the login `


## premium_subscription

**Label:** Premium Subscription  
**Training count:** 1,943 (6.8%)  
**Definition:** Premium plan questions: status, cancellation, trial, plan type.  
**Escalation policy:** AUTO_HANDLE for status queries; ESCALATE if billing dispute.  
**Example:** `@SpotifyCares i love spotify but spotify premium costs too much`


## billing_charge

**Label:** Billing Charge  
**Training count:** 1,613 (5.6%)  
**Definition:** Unexpected charge, payment failure, refund request.  
**Escalation policy:** ESCALATE for disputes or unauthorized charges.  
**Example:** `@115888 What about military members? We make basically no money.`


## app_crash_bug

**Label:** App Crash Bug  
**Training count:** 614 (2.1%)  
**Definition:** App crashes, freezes, black screen, glitch, error.  
**Escalation policy:** AUTO_HANDLE -- reinstall/update steps.  
**Example:** `@SpotifyCares Where do I report broken songs (static over parts of it)? I have several`


## playlist_library

**Label:** Playlist Library  
**Training count:** 1,712 (6.0%)  
**Definition:** Playlist or saved songs missing, deleted, or not syncing.  
**Escalation policy:** AUTO_HANDLE -- re-login/sync steps; ESCALATE if data loss confirmed.  
**Example:** `@115888 in the new web app style I cannot find the option for ordering albums by "most recent added" (=added into my lib`


## content_unavailable

**Label:** Content Unavailable  
**Training count:** 699 (2.4%)  
**Definition:** Song/album/artist unavailable due to region or removal.  
**Escalation policy:** AUTO_HANDLE -- licensing restrictions cannot be overridden.  
**Example:** `@SpotifyCares For example in playlists I no longer see/identify the songs that were saved before. UI is too large, hard `


## device_platform

**Label:** Device Platform  
**Training count:** 2,160 (7.6%)  
**Definition:** Spotify not working on a specific device (speaker, TV, phone OS, console).  
**Escalation policy:** AUTO_HANDLE with device-specific steps.  
**Example:** `@spotifycares my amazon echo wont connect to spotify, please help`


## offline_download

**Label:** Offline Download  
**Training count:** 848 (3.0%)  
**Definition:** Downloaded songs unavailable offline or download failures.  
**Escalation policy:** AUTO_HANDLE; ESCALATE if premium active but offline fails.  
**Example:** `@SpotifyCares @112253   it says not available in offline mode ... its never done this before`
