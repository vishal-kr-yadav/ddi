"""
SQLite Database
===============
File-based, zero-setup. Stores every fact-check result and tracks
search frequency for trending + shareable URLs.
"""

import sqlite3
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "ddi.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS fact_checks (
                id                  TEXT PRIMARY KEY,
                claim               TEXT NOT NULL,
                verdict             TEXT,
                confidence          INTEGER,
                verdict_explanation TEXT,
                summary             TEXT,
                guidance            TEXT,
                key_findings        TEXT,
                articles            TEXT,
                sources_searched    INTEGER,
                processing_time     REAL,
                created_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS searches (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_check_id   TEXT    NOT NULL,
                claim_normalized TEXT   NOT NULL,
                searched_at     TEXT    DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_searches_time
                ON searches(searched_at);
            CREATE INDEX IF NOT EXISTS idx_checks_created
                ON fact_checks(created_at);
        """)
    logger.info(f"Database ready at {DB_PATH}")


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

async def store_result(result: dict):
    def _run():
        with _conn() as c:
            c.execute("""
                INSERT OR REPLACE INTO fact_checks
                    (id, claim, verdict, confidence, verdict_explanation,
                     summary, guidance, key_findings, articles,
                     sources_searched, processing_time)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                result["id"],
                result["claim"],
                result.get("verdict", "UNVERIFIED"),
                result.get("confidence", 0),
                result.get("verdict_explanation", ""),
                result.get("summary", ""),
                result.get("guidance", ""),
                json.dumps(result.get("key_findings", [])),
                json.dumps(result.get("articles", [])),
                result.get("sources_searched", 0),
                result.get("processing_time", 0),
            ))
            # Record the search for trending
            c.execute("""
                INSERT INTO searches (fact_check_id, claim_normalized)
                VALUES (?, ?)
            """, (result["id"], result["claim"].lower().strip()))
    await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

async def get_by_id(fact_check_id: str) -> Optional[dict]:
    def _run():
        with _conn() as c:
            row = c.execute(
                "SELECT * FROM fact_checks WHERE id = ?", (fact_check_id,)
            ).fetchone()
            if row:
                d = dict(row)
                d["key_findings"] = json.loads(d["key_findings"] or "[]")
                d["articles"]     = json.loads(d["articles"]     or "[]")
                return d
        return None
    return await asyncio.to_thread(_run)


async def get_trending(limit: int = 5) -> list:
    def _run():
        with _conn() as c:
            rows = c.execute("""
                SELECT
                    fc.id, fc.claim, fc.verdict, fc.confidence,
                    fc.verdict_explanation, COUNT(s.id) AS check_count
                FROM searches s
                JOIN fact_checks fc ON s.fact_check_id = fc.id
                WHERE s.searched_at > datetime('now', '-24 hours')
                GROUP BY fc.id
                ORDER BY check_count DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    return await asyncio.to_thread(_run)


async def get_recent(limit: int = 8) -> list:
    def _run():
        with _conn() as c:
            rows = c.execute("""
                SELECT id, claim, verdict, confidence, created_at
                FROM fact_checks
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
    return await asyncio.to_thread(_run)
