"""
Source Credibility Scoring
==========================
Maps news source names / domains to a trust score (0–100) and a tier label.
Used to badge each article and to signal Claude which sources carry more weight.

Tiers:
  90–100  Highly Credible   (green)  — wire services, major international broadcasters
  75–89   Credible          (blue)   — established national outlets
  60–74   Mixed             (yellow) — outlets with known bias or uneven accuracy
  0–59    Low Credibility   (red)    — tabloids, partisan blogs, unreliable aggregators
  None    Unrated           (gray)   — source not in our database yet
"""

from typing import Optional

# ---------------------------------------------------------------------------
# Source database  (lowercase keys for case-insensitive matching)
# ---------------------------------------------------------------------------
CREDIBILITY_DB: dict[str, int] = {
    # ── Wire / Newswire services ──────────────────────────────────────────
    "reuters":                   97,
    "associated press":          96,
    "ap news":                   96,
    "ap":                        96,
    "afp":                       94,
    "bloomberg":                 93,
    "bloomberg news":            93,

    # ── International broadcasters ────────────────────────────────────────
    "bbc":                       95,
    "bbc news":                  95,
    "bbc world service":         95,
    "npr":                       93,
    "pbs":                       91,
    "pbs newshour":              91,
    "france 24":                 88,
    "dw":                        88,
    "deutsche welle":            88,
    "al jazeera":                85,
    "al jazeera english":        85,
    "abc news australia":        88,
    "abc australia":             88,
    "radio free europe":         83,
    "rfe/rl":                    83,
    "voice of america":          82,
    "voa":                       82,
    "euronews":                  82,
    "channel newsasia":          82,
    "cna":                       82,
    "nhk world":                 87,
    "nhk":                       87,

    # ── USA — Major outlets ───────────────────────────────────────────────
    "new york times":            90,
    "the new york times":        90,
    "nytimes.com":               90,
    "washington post":           89,
    "the washington post":       89,
    "wall street journal":       90,
    "wsj":                       90,
    "financial times":           91,
    "the atlantic":              85,
    "the new yorker":            87,
    "time":                      84,
    "newsweek":                  76,
    "usa today":                 81,
    "los angeles times":         84,
    "chicago tribune":           81,
    "politico":                  83,
    "axios":                     85,
    "the guardian":              88,
    "guardian":                  88,
    "cnn":                       79,
    "msnbc":                     73,
    "nbc news":                  82,
    "abc news":                  82,
    "cbs news":                  82,
    "fox news":                  65,
    "the hill":                  76,
    "vox":                       78,
    "slate":                     74,
    "huffpost":                  68,
    "huffington post":           68,
    "buzzfeed news":             66,
    "daily beast":               65,
    "vice":                      68,
    "mother jones":              72,
    "the intercept":             72,
    "propublica":                88,
    "breitbart":                 38,
    "daily wire":                42,
    "the blaze":                 38,
    "infowars":                  10,
    "newsmax":                   45,
    "oann":                      35,

    # ── Europe ────────────────────────────────────────────────────────────
    "the economist":             92,
    "economist":                 92,
    "the telegraph":             76,
    "the times":                 83,
    "the independent":           76,
    "the mirror":                55,
    "daily mail":                52,
    "the sun":                   45,
    "sky news":                  80,
    "itv news":                  80,
    "le monde":                  88,
    "der spiegel":               87,
    "spiegel":                   87,
    "frankfurter allgemeine":    87,
    "faz":                       87,
    "süddeutsche zeitung":       86,
    "le figaro":                 81,
    "liberation":                78,
    "el pais":                   85,
    "corriere della sera":       83,
    "la repubblica":             82,
    "nrc":                       85,
    "svt":                       88,
    "yle":                       89,
    "rts":                       87,
    "ard":                       88,
    "zdf":                       88,
    "rtbf":                      84,

    # ── Asia ─────────────────────────────────────────────────────────────
    "the hindu":                 85,
    "hindu":                     85,
    "hindustan times":           78,
    "times of india":            75,
    "ndtv":                      78,
    "the wire":                  76,
    "scroll.in":                 76,
    "the print":                 77,
    "dawn":                      82,
    "geo news":                  76,
    "south china morning post":  80,
    "scmp":                      80,
    "japan times":               83,
    "nikkei":                    88,
    "nikkei asia":               88,
    "the straits times":         83,
    "straits times":             83,
    "the star":                  74,
    "bangkok post":              76,
    "the nation":                72,
    "jakarta post":              75,
    "philippine daily inquirer": 74,
    "korea times":               74,
    "korea herald":              74,
    "yonhap":                    82,
    "xinhua":                    50,  # state media
    "cgtn":                      48,  # state media
    "global times":              40,  # state media

    # ── Aggregators / Search ──────────────────────────────────────────────
    "google news":               72,
    "google news (usa)":         72,
    "google news (europe/uk)":   72,
    "google news (asia/india)":  72,
    "gdelt":                     68,
    "msn":                       60,
    "yahoo news":                60,
}

# Tier definitions: (min_score, label, color)
TIERS = [
    (90, "Highly Credible", "green"),
    (75, "Credible",        "blue"),
    (60, "Mixed",           "yellow"),
    (0,  "Low Credibility", "red"),
]


def get_credibility(source_name: str) -> dict:
    """
    Returns {"score": int|None, "tier": str, "color": str}
    for a given source name.
    """
    if not source_name:
        return {"score": None, "tier": "Unrated", "color": "gray"}

    key = source_name.lower().strip()

    # 1. Exact match
    score: Optional[int] = CREDIBILITY_DB.get(key)

    # 2. Partial match (key contained in source name or vice-versa)
    if score is None:
        for db_key, db_score in CREDIBILITY_DB.items():
            if db_key in key or key in db_key:
                score = db_score
                break

    # 3. Domain fragment match (e.g. "reuters.com" → "reuters")
    if score is None:
        for db_key, db_score in CREDIBILITY_DB.items():
            if db_key.replace(" ", "") in key.replace(".", "").replace("-", "").replace(" ", ""):
                score = db_score
                break

    if score is None:
        return {"score": None, "tier": "Unrated", "color": "gray"}

    for threshold, tier, color in TIERS:
        if score >= threshold:
            return {"score": score, "tier": tier, "color": color}

    return {"score": score, "tier": "Low Credibility", "color": "red"}
