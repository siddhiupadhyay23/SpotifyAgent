"""
Central configuration for the SpotifyCares Support Agent.
All paths, constants, and tunables live here.
"""
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent
DATA_DIR    = ROOT / "data"
PROC_DIR    = DATA_DIR / "processed"
GOLDEN_DIR  = ROOT / "golden_set"
RETRIEVAL_DIR = ROOT / "retrieval"
EVAL_DIR    = ROOT / "evaluation"
RESULTS_DIR = ROOT / "results"
DOCS_DIR    = ROOT / "docs"

RAW_CSV     = Path(r"C:\Users\Siddhi\Desktop\Hiver\twcs\twcs.csv")

CORPUS_FILE      = PROC_DIR / "retrieval_corpus.jsonl"
TRAIN_FILE       = PROC_DIR / "train_conversations.jsonl"
GOLDEN_FILE      = GOLDEN_DIR / "golden_set.jsonl"
GOLDEN_CSV       = GOLDEN_DIR / "golden_set.csv"
INTENT_TAXONOMY  = DOCS_DIR  / "intent_taxonomy.json"
CHROMA_DIR       = RETRIEVAL_DIR / "chroma_db"
RESULTS_JSON     = RESULTS_DIR / "all_results.json"
DECISIONS_FILE   = DOCS_DIR / "engineering_decisions.md"

# ── Brand ─────────────────────────────────────────────────────────────────────
BRAND = "SpotifyCares"

# ── Temporal split ────────────────────────────────────────────────────────────
# Data spans 2013-09 to 2017-12.
# Use first 80% of conversations (by date) as retrieval corpus.
# Use last 20% as pool for golden set construction.
TRAIN_CUTOFF_PCT = 0.80   # 80% oldest conversations → retrieval corpus

# ── Intent taxonomy ───────────────────────────────────────────────────────────
INTENTS = [
    "playback_error",
    "account_login",
    "premium_subscription",
    "billing_charge",
    "app_crash_bug",
    "playlist_library",
    "content_unavailable",
    "device_platform",
    "offline_download",
]

INTENT_LABELS = {
    "playback_error":      "Playback Error",
    "account_login":       "Account / Login",
    "premium_subscription":"Premium / Subscription",
    "billing_charge":      "Billing / Charge",
    "app_crash_bug":       "App Crash / Bug",
    "playlist_library":    "Playlist / Library",
    "content_unavailable": "Content Unavailable",
    "device_platform":     "Device / Platform",
    "offline_download":    "Offline / Download",
}

# Target golden-set counts per intent (total ≈ 200)
GOLDEN_PER_INTENT = {
    "playback_error":      30,
    "account_login":       28,
    "premium_subscription":27,
    "billing_charge":      22,
    "app_crash_bug":       20,
    "playlist_library":    25,
    "content_unavailable": 18,
    "device_platform":     18,
    "offline_download":    12,
}  # total = 200

# ── Platform extraction ───────────────────────────────────────────────────────
import re

PLATFORM_PATTERNS = {
    "ios":      re.compile(r'\b(ios|iphone|ipad|apple\s+music|siri)\b', re.I),
    "android":  re.compile(r'\b(android|samsung|galaxy|pixel|oneplus|xiaomi|huawei|redmi)\b', re.I),
    "windows":  re.compile(r'\b(windows|pc|desktop|laptop)\b', re.I),
    "mac":      re.compile(r'\b(mac|macos|macbook|imac)\b', re.I),
    "speaker":  re.compile(r'\b(alexa|echo|google\s+home|sonos|bose)\b', re.I),
    "tv":       re.compile(r'\b(tv|chromecast|firetv|fire\s+stick|smart\s+tv|roku|apple\s+tv)\b', re.I),
    "car":      re.compile(r'\b(car|vehicle|carplay|android\s+auto)\b', re.I),
    "ps":       re.compile(r'\b(ps[34]|playstation)\b', re.I),
    "web":      re.compile(r'\b(browser|chrome|firefox|safari|web\s+player|website)\b', re.I),
}

def extract_platform(text: str) -> str:
    """Return the first matched platform or 'unknown'."""
    for plat, pat in PLATFORM_PATTERNS.items():
        if pat.search(text or ""):
            return plat
    return "unknown"

# ── Escalation ────────────────────────────────────────────────────────────────
# Threshold calibrated on validation set during evaluation
ESCALATION_CONFIDENCE_THRESHOLD = 0.60  # updated after calibration run

HIGH_RISK_INTENTS = {"billing_charge", "account_login"}  # extra scrutiny

ESCALATION_KEYWORDS = re.compile(
    r'\b(hack|hacked|compromis|unauthor|stolen|fraud|'
    r'chargeback|dispute|charge.?back|'
    r'cannot\s+access|account\s+stolen|'
    r'legal|lawyer|sue|refund\s+or\s+else|never\s+again)\b',
    re.I
)

# ── DM-filter ─────────────────────────────────────────────────────────────────
# Responses that are ONLY a DM redirect with no other content
DM_ONLY_PATTERN = re.compile(
    r'^[^.!?]{0,80}(DM|direct\s*message|send\s*us\s*a\s*message|message\s*us)[^.!?]{0,80}$',
    re.I
)

# ── Retrieval ─────────────────────────────────────────────────────────────────
EMBED_MODEL   = "all-MiniLM-L6-v2"   # fast, 384-dim, good quality
RETRIEVAL_K   = 5                     # candidates before platform rerank
RETRIEVAL_TOP = 3                     # final top-k used for generation

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MODEL       = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS  = 300

# ── Evaluation ────────────────────────────────────────────────────────────────
JUDGE_SAMPLE_SIZE   = 60   # LLM-judge on this many golden examples
HUMAN_AGREE_SIZE    = 30   # human agreement subset
RANDOM_SEED         = 42
