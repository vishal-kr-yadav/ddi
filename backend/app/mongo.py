import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

logger = logging.getLogger(__name__)

# ── Client & DB references (set on startup) ──────────────────────────────
_client: Optional[AsyncIOMotorClient] = None
_db = None


def get_client():
    return _client


async def init_mongo():
    global _client, _db
    logger.info(f"Connecting to MongoDB: {settings.MONGO_DB}")
    _client = AsyncIOMotorClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )
    _db = _client[settings.MONGO_DB]

    # Quick ping — single attempt, don't block startup on failure
    try:
        await _client.admin.command("ping")
        logger.info("MongoDB ping OK")
    except Exception as e:
        logger.warning(f"MongoDB ping failed (will retry lazily): {e}")

    # Indexes — best effort
    try:
        await _db.users.create_index("email", unique=True)
        await _db.fact_checks.create_index("email")
        await _db.fact_checks.create_index("created_at")
        await _db.activity_logs.create_index("email")
        await _db.activity_logs.create_index("timestamp")
    except Exception as e:
        logger.warning(f"Index creation deferred: {e}")


async def close_mongo():
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def _now():
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════
# USERS
# ═══════════════════════════════════════════════════════════════════════════

async def create_user(email: str) -> Dict[str, Any]:
    doc = {
        "email": email,
        "registered_at": _now(),
        "last_login_at": _now(),
    }
    await _db.users.insert_one(doc)
    return doc


async def get_user(email: str) -> Optional[Dict[str, Any]]:
    return await _db.users.find_one({"email": email})


async def update_last_login(email: str):
    await _db.users.update_one(
        {"email": email},
        {"$set": {"last_login_at": _now()}},
    )


# ═══════════════════════════════════════════════════════════════════════════
# FACT CHECKS
# ═══════════════════════════════════════════════════════════════════════════

async def store_fact_check(result: Dict[str, Any], email: str):
    doc = {
        "_id": result["id"],
        "email": email,
        "claim": result["claim"],
        "verdict": result.get("verdict", "UNVERIFIED"),
        "confidence": result.get("confidence", 0),
        "verdict_explanation": result.get("verdict_explanation", ""),
        "summary": result.get("summary", ""),
        "guidance": result.get("guidance", ""),
        "key_findings": result.get("key_findings", []),
        "articles": result.get("articles", []),
        "sources_searched": result.get("sources_searched", 0),
        "processing_time": result.get("processing_time", 0),
        "created_at": _now(),
    }
    await _db.fact_checks.replace_one({"_id": doc["_id"]}, doc, upsert=True)


async def get_fact_check_by_id(fact_check_id: str) -> Optional[Dict[str, Any]]:
    doc = await _db.fact_checks.find_one({"_id": fact_check_id})
    if doc:
        doc["id"] = doc.pop("_id")
    return doc


async def get_user_history(email: str, limit: int = 20) -> List[Dict[str, Any]]:
    cursor = _db.fact_checks.find(
        {"email": email},
        {"_id": 1, "claim": 1, "verdict": 1, "confidence": 1, "created_at": 1},
    ).sort("created_at", -1).limit(limit)

    results = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")
        results.append(doc)
    return results


async def get_trending(limit: int = 5) -> List[Dict[str, Any]]:
    cutoff = _now() - timedelta(hours=24)
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"claim": {"$toLower": "$claim"}},
            "fact_check_id": {"$first": "$_id"},
            "claim": {"$first": "$claim"},
            "verdict": {"$first": "$verdict"},
            "confidence": {"$first": "$confidence"},
            "check_count": {"$sum": 1},
        }},
        {"$sort": {"check_count": -1}},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "id": "$fact_check_id",
            "claim": 1,
            "verdict": 1,
            "confidence": 1,
            "check_count": 1,
        }},
    ]
    results = []
    async for doc in _db.fact_checks.aggregate(pipeline):
        results.append(doc)
    return results


async def get_recent(limit: int = 8) -> List[Dict[str, Any]]:
    cursor = _db.fact_checks.find(
        {},
        {"_id": 1, "claim": 1, "verdict": 1, "confidence": 1, "created_at": 1},
    ).sort("created_at", -1).limit(limit)

    results = []
    async for doc in cursor:
        doc["id"] = doc.pop("_id")
        results.append(doc)
    return results


# ═══════════════════════════════════════════════════════════════════════════
# USAGE / RATE LIMIT
# ═══════════════════════════════════════════════════════════════════════════

async def get_weekly_usage(email: str) -> Dict[str, Any]:
    cutoff = _now() - timedelta(days=7)
    count = await _db.fact_checks.count_documents({
        "email": email,
        "created_at": {"$gte": cutoff},
    })
    remaining = max(0, settings.WEEKLY_FACT_CHECK_LIMIT - count)

    # Find when the oldest check in the window expires
    resets_at = None
    if count > 0:
        oldest = await _db.fact_checks.find_one(
            {"email": email, "created_at": {"$gte": cutoff}},
            sort=[("created_at", 1)],
        )
        if oldest:
            resets_at = (oldest["created_at"] + timedelta(days=7)).isoformat()

    return {
        "email": email,
        "checks_used": count,
        "checks_remaining": remaining,
        "resets_at": resets_at,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ACTIVITY LOGS
# ═══════════════════════════════════════════════════════════════════════════

async def log_activity(email: str, action: str, details: Optional[Dict] = None):
    doc = {
        "email": email,
        "action": action,
        "details": details or {},
        "timestamp": _now(),
    }
    await _db.activity_logs.insert_one(doc)
