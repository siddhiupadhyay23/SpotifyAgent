"""
Human annotation tool for golden_set/human_review.csv
Run: streamlit run annotate.py
"""
import csv, pathlib, streamlit as st

CSV_PATH = pathlib.Path(__file__).parent / "golden_set" / "human_review.csv"

INTENTS = [
    "",                   # blank = not yet labelled
    "playback_error",
    "device_platform",
    "premium_subscription",
    "playlist_library",
    "billing_charge",
    "account_login",
    "offline_download",
    "content_unavailable",
    "app_crash_bug",
]

ESCALATION = ["", "AUTO_HANDLE", "ESCALATE"]

# ── load ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_rows():
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def save_rows(rows):
    fields = list(rows[0].keys())
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

# ── session state ─────────────────────────────────────────────────
if "rows" not in st.session_state:
    st.session_state.rows = load_rows()

rows = st.session_state.rows
n    = len(rows)

# Find first unlabelled example as default starting position
def first_unlabelled():
    for i, r in enumerate(rows):
        if not r["human_intent"] or not r["human_escalation"]:
            return i
    return 0

if "idx" not in st.session_state:
    st.session_state.idx = first_unlabelled()

idx = st.session_state.idx
row = rows[idx]

# ── progress stats ────────────────────────────────────────────────
completed = sum(
    1 for r in rows
    if r["human_intent"].strip() and r["human_escalation"].strip()
)
remaining = n - completed
pct       = int(100 * completed / n)

# ── layout ────────────────────────────────────────────────────────
st.set_page_config(page_title="Golden Set Annotator", layout="centered")
st.title("Golden Set Annotation")

# Progress bar
st.progress(pct / 100)
col1, col2, col3 = st.columns(3)
col1.metric("Completed", f"{completed} / {n}")
col2.metric("Remaining", remaining)
col3.metric("Progress", f"{pct}%")

st.divider()

# Example header
st.subheader(f"Example {idx + 1} of {n}  ·  ID: {row['golden_id']}")
if row["confidence_note"]:
    st.warning(f"⚠ {row['confidence_note']}")

# Customer message — prominent
st.markdown("**Customer message:**")
st.info(row["customer_msg"])

# Proposed label (read-only reference)
col_a, col_b = st.columns(2)
col_a.markdown(f"**Proposed intent:** `{row['auto_intent']}`")
col_b.markdown(f"**Proposed escalation:** `{row['auto_escalation']}`")
if row["platform"] and row["platform"] != "unknown":
    st.caption(f"Platform detected: {row['platform']}")

st.divider()

# ── Human intent selector ──────────────────────────────────────
current_intent = row["human_intent"].strip() if row["human_intent"].strip() in INTENTS else ""
intent_idx = INTENTS.index(current_intent) if current_intent in INTENTS else 0

human_intent = st.selectbox(
    "Human intent  *(select — do not rely on proposed label)*",
    options=INTENTS,
    index=intent_idx,
    format_func=lambda x: "— select —" if x == "" else x,
    key=f"intent_{idx}",
)

# ── Human escalation ──────────────────────────────────────────
current_esc = row["human_escalation"].strip() if row["human_escalation"].strip() in ESCALATION else ""
esc_idx = ESCALATION.index(current_esc) if current_esc in ESCALATION else 0

human_esc = st.radio(
    "Human escalation decision",
    options=["AUTO_HANDLE", "ESCALATE"],
    index=0 if current_esc != "ESCALATE" else 1,
    horizontal=True,
    key=f"esc_{idx}",
)

# ── Notes ────────────────────────────────────────────────────
notes = st.text_area(
    "Reviewer notes (optional)",
    value=row.get("reviewer_notes", ""),
    height=80,
    key=f"notes_{idx}",
)

# ── Navigation buttons ────────────────────────────────────────
st.divider()
btn_prev, btn_save, btn_skip = st.columns([1, 2, 1])

with btn_prev:
    if st.button("← Previous", disabled=(idx == 0)):
        st.session_state.idx = idx - 1
        st.rerun()

with btn_save:
    save_label = "Save & Next →" if idx < n - 1 else "Save (last example)"
    if st.button(save_label, type="primary"):
        if not human_intent:
            st.error("Please select an intent before saving.")
        else:
            rows[idx]["human_intent"]     = human_intent
            rows[idx]["human_escalation"] = human_esc
            rows[idx]["reviewer_notes"]   = notes
            save_rows(rows)
            # Clear cache so next load reflects saved state
            load_rows.clear()
            st.success(f"Saved [{row['golden_id']}] → {human_intent} / {human_esc}")
            if idx < n - 1:
                st.session_state.idx = idx + 1
                st.rerun()

with btn_skip:
    if st.button("Skip →", disabled=(idx == n - 1)):
        st.session_state.idx = idx + 1
        st.rerun()

# Jump to example by ID
st.divider()
with st.expander("Jump to example"):
    jump = st.number_input("Example number", min_value=1, max_value=n, value=idx + 1, step=1)
    if st.button("Go"):
        st.session_state.idx = int(jump) - 1
        st.rerun()
