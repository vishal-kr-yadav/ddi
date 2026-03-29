import logging
from typing import Dict, Any

from app.config import settings
from app.mongo import (
    create_user, get_user, update_last_login,
    get_weekly_usage, log_activity,
)

logger = logging.getLogger(__name__)


async def register_user(email: str) -> Dict[str, Any]:
    existing = await get_user(email)
    if existing:
        raise ValueError("Email already registered.")
    await create_user(email)
    await log_activity(email, "register")
    return {
        "email": email,
        "registered_at": "",
        "checks_remaining": settings.WEEKLY_FACT_CHECK_LIMIT,
        "message": "Registration successful.",
    }


async def validate_user(email: str) -> Dict[str, Any]:
    user = await get_user(email)
    if not user:
        raise ValueError("Email not registered.")
    await update_last_login(email)
    usage = await get_weekly_usage(email)
    return {
        "email": email,
        "registered_at": str(user.get("registered_at", "")),
        "checks_used": usage["checks_used"],
        "checks_remaining": usage["checks_remaining"],
        "resets_at": usage["resets_at"],
    }


async def check_rate_limit(email: str) -> Dict[str, Any]:
    user = await get_user(email)
    if not user:
        raise ValueError("Email not registered.")
    usage = await get_weekly_usage(email)
    return {
        "allowed": usage["checks_remaining"] > 0,
        "checks_used": usage["checks_used"],
        "checks_remaining": usage["checks_remaining"],
        "resets_at": usage["resets_at"],
    }


async def record_usage(email: str, claim: str, fact_check_id: str) -> Dict[str, Any]:
    await log_activity(email, "fact_check", {
        "claim": claim,
        "fact_check_id": fact_check_id,
    })
    return await get_weekly_usage(email)


async def get_usage(email: str) -> Dict[str, Any]:
    user = await get_user(email)
    if not user:
        raise ValueError("Email not registered.")
    return await get_weekly_usage(email)
