# Human Labeling Guide: Spotify Customer Support Golden Set

This guide provides instructions for manually reviewing and labeling the 200 evaluation examples in `golden_set/human_review_form.csv`.

---

## 1. Overview & Workflow

The golden evaluation set requires genuine human ground truth. Do not automatically copy or rely on proposed values without independent verification.

### Form Structure (`golden_set/human_review_form.csv`)
- **`id`**: Unique example ID (`g0001` – `g0200`).
- **`customer_message`**: The customer's message or tweet.
- **`conversation_context`**: The brand response and prior conversation turns (if available).
- **`proposed_intent`**: Proposed intent baseline (for reference only).
- **`human_intent`**: **Fill this.** Enter one of the 9 allowed intent labels.
- **`proposed_escalation`**: Proposed escalation baseline (`AUTO_HANDLE` or `ESCALATE`).
- **`human_escalation`**: **Fill this.** Enter `AUTO_HANDLE` or `ESCALATE`.
- **`notes`**: Optional reviewer notes (e.g., edge cases, ambiguities, or secondary intents).

> **Ordering**: Rows are sorted so that the most uncertain cases (model/rule disagreements, multi-intent matches, and low-context examples) appear at the top. The cleanest, high-agreement cases appear at the bottom.

---

## 2. The 9 Allowed Intents

Reviewers must select exactly one of the following 9 canonical taxonomy labels for `human_intent`:

| Intent Label | Description & Typical Triggers |
|---|---|
| **`playback_error`** | Issues streaming or playing music: song won't play, continuous buffering, random pauses/skipping, no audio output, playback stuttering, or track restarts unexpectedly. |
| **`account_login`** | Authentication and credential problems: cannot sign in, password reset issues, locked accounts, email changed without permission, country code mismatch on login, or compromised/hacked accounts. |
| **`premium_subscription`** | Paid tier plans and status: subscription management, Free vs. Premium features, Family/Duo plan member invites, student discount verification, renewal dates, or plan cancellations. |
| **`billing_charge`** | Monetary and transactional issues: unexpected charges, double billing, payment method failures, refund requests, price disputes, or unauthorized transactions. |
| **`app_crash_bug`** | Application stability and UI bugs: app crashing on startup, freezing/hanging, force-closing, black screens, UI glitches, or failing to install/update properly. |
| **`playlist_library`** | Organization and catalog curation: playlists disappearing or deleted, saved/liked songs missing, unable to add songs to a playlist, library sync failures, or queue management. |
| **`content_unavailable`** | Specific catalog availability limitations: songs, albums, or artists greyed out or missing due to regional licensing, country restrictions, or takedowns. |
| **`device_platform`** | Device-specific hardware, OS, or ecosystem integration: compatibility issues on iOS, Android, Windows, Mac, Apple Watch, Sonos, Chromecast, Alexa/Echo, Smart TVs, consoles, or CarPlay. |
| **`offline_download`** | Local storage and offline playback: songs failing to download, downloaded tracks disappearing ("undownloading"), offline mode not functioning, or SD card/cache storage limits. |

---

## 3. How to Choose an Intent from Customer Message and Context

1. **Read the `customer_message` first**:
   - Determine what the customer is attempting to achieve or complaining about.
   - Look for the primary failure mode rather than incidental phrasing.

2. **Examine the `conversation_context`**:
   - `conversation_context` contains the actual response provided by Spotify support (`@SpotifyCares`) and any prior messages in the thread.
   - Use the support agent's diagnosis to disambiguate vague customer wording (e.g., if a customer says "it's not working" and the agent provides steps for clearing local offline cache, the issue is likely `offline_download`).
   - Identify whether the agent identified an account issue, a catalog gap, or an app bug.

3. **Distinguish Root Cause vs. Incidental Mentions**:
   - *Example*: "I pay for Premium but my app crashes whenever I open it."
     - Incidental mention: Premium status (used to express frustration).
     - Root cause: Application crash.
     - **Correct Intent**: `app_crash_bug`.
   - *Example*: "My downloaded songs aren't playing on my iPhone."
     - Incidental mention: iPhone (device context).
     - Root cause: Offline playback failure.
     - **Correct Intent**: `offline_download`.

---

## 4. How to Choose `AUTO_HANDLE` vs. `ESCALATE`

Choose between `AUTO_HANDLE` and `ESCALATE` for `human_escalation`:

### Mark `ESCALATE` when:
- **Security & Compromise**: Customer reports hacked accounts, unauthorized email/password changes, or unfamiliar devices playing music.
- **Financial Disputes**: Customer disputes charges, reports unauthorized payments, demands refunds, or mentions bank chargebacks.
- **Legal Threats**: Customer mentions lawyers, lawsuits, consumer protection boards, or regulatory actions.
- **Private Data Required**: Issue cannot be resolved without exchanging private personal identifiable information (PII) or accessing internal backend systems via direct message (DM).
- **High Uncertainty / Safety Risk**: When unsure whether automated advice could harm the user's account or finances, choose `ESCALATE`.

### Mark `AUTO_HANDLE` when:
- **Standard Troubleshooting**: Self-service steps can resolve the problem (reinstalling, clearing cache, checking network settings, restarting device).
- **Public Guidance / Education**: Explaining how a feature works, sharing links to the Spotify Community or "Spotify Ideas" suggestion board.
- **Catalog Availability Explanations**: Clarifying regional licensing restrictions or artist availability.
- **General Product Feedback**: Non-dispute comments regarding app updates, UI changes, or feature requests.

---

## 5. What to Do When Multiple Intents Are Present

When a message touches multiple topics:

1. **Identify the Primary Blocker / Action Request**:
   - Select the intent representing the action the customer wants taken or the obstacle preventing them from using the service.
   - *Example*: "Someone hacked into my account and deleted my playlists."
     - Both `account_login` and `playlist_library` are mentioned.
     - The initiating security breach is the primary driver.
     - **Intent**: `account_login` (with `ESCALATE`).

2. **Priority Hierarchy for Severe Conflicts**:
   - If two intents carry equal weight in the customer's request, break ties in favor of higher risk/specialization:
     1. `account_login` (Security)
     2. `billing_charge` (Financial)
     3. `app_crash_bug` / `offline_download` (Critical Functionality)
     4. `playlist_library` / `content_unavailable` / `device_platform` / `playback_error`
     5. `premium_subscription` (General Inquiry)

3. **Document in `notes`**:
   - Record the secondary intent in the `notes` column (e.g., `Secondary: playlist_library`).

---

## 6. What to Do When Context Is Insufficient

In social media datasets, customer messages can be short or fragmentary (e.g., "@SpotifyCares Windows 10, Chrome" or "Still not working :/").

1. **Leverage `conversation_context`**:
   - Read the agent reply. If the agent asks for specific login details, the issue relates to `account_login`. If the agent suggests a clean reinstall, refer to the underlying app or playback problem.
2. **Inspect Prior Conversation**:
   - If prior context is shown (prefixed with `[Prior Context]`), read the initial exchange that led to the follow-up message.
3. **If Context Remains Genuinely Ambiguous**:
   - Assign the most plausible intent based on the available tokens.
   - For escalation: if safety or financial risk cannot be determined due to complete ambiguity, default to `AUTO_HANDLE` unless private details are requested by support.
   - **Mandatory Note**: Add a brief note in `notes` describing the ambiguity (e.g., `Low context; inferred device_platform from OS mention`).
