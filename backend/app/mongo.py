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

    # Quick ping
    try:
        await _client.admin.command("ping")
        logger.info("MongoDB ping OK")
    except Exception as e:
        logger.warning(f"MongoDB ping failed (will retry lazily): {e}")

    # Indexes — best effort
    try:
        await _db.fact_checks.create_index("created_at")
        await _db.device_usage.create_index("device_id")
        await _db.device_usage.create_index("checked_at")
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
# DEVICE USAGE (rate limiting by device ID)
# ═══════════════════════════════════════════════════════════════════════════

async def record_device_check(device_id: str):
    """Record that a device performed a fact-check."""
    await _db.device_usage.insert_one({
        "device_id": device_id,
        "checked_at": _now(),
    })


async def get_device_usage(device_id: str) -> Dict[str, Any]:
    """Get usage stats for a device in the last 24 hours."""
    cutoff = _now() - timedelta(hours=24)
    count = await _db.device_usage.count_documents({
        "device_id": device_id,
        "checked_at": {"$gte": cutoff},
    })
    remaining = max(0, settings.DAILY_DEVICE_LIMIT - count)

    resets_at = None
    if count > 0:
        oldest = await _db.device_usage.find_one(
            {"device_id": device_id, "checked_at": {"$gte": cutoff}},
            sort=[("checked_at", 1)],
        )
        if oldest:
            resets_at = (oldest["checked_at"] + timedelta(hours=24)).isoformat()

    return {
        "device_id": device_id,
        "checks_used": count,
        "checks_remaining": remaining,
        "limit": settings.DAILY_DEVICE_LIMIT,
        "resets_at": resets_at,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FACT CHECKS
# ═══════════════════════════════════════════════════════════════════════════

async def store_fact_check(result: Dict[str, Any], device_id: str):
    doc = {
        "_id": result["id"],
        "device_id": device_id,
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
