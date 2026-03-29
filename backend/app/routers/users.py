import re
import logging
from fastapi import APIRouter, HTTPException

from app.models.user_schemas import (
    EmailRequest, OtpVerifyRequest, OtpSentResponse,
    RegisterResponse, LoginResponse, UsageResponse,
)
from app.services.user_store import register_user, validate_user, get_usage
from app.services.otp_service import generate_and_send_otp, verify_otp
from app.mongo import log_activity

router = APIRouter()
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def _clean_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format.")
    return email


# ---------------------------------------------------------------------------
# Step 1: Send OTP for registration
# ---------------------------------------------------------------------------
@router.post("/users/register", response_model=OtpSentResponse)
async def user_register(req: EmailRequest):
    email = _clean_email(req.email)
    # Check if already registered
    try:
        await validate_user(email)
        raise HTTPException(status_code=409, detail="Email already registered. Please sign in.")
    except ValueError:
        pass  # Not registered — good, proceed

    try:
        await generate_and_send_otp(email, "register")
        await log_activity(email, "otp_sent", {"purpose": "register"})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to send OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again.")

    return OtpSentResponse(message="OTP sent to your email.", email=email)


# ---------------------------------------------------------------------------
# Step 2: Verify OTP and complete registration
# ---------------------------------------------------------------------------
@router.post("/users/verify-register", response_model=RegisterResponse, status_code=201)
async def user_verify_register(req: OtpVerifyRequest):
    email = _clean_email(req.email)
    otp = req.otp.strip()

    if not verify_otp(email, otp):
        await log_activity(email, "otp_failed", {"purpose": "register"})
        raise HTTPException(status_code=400, detail="Invalid or expired OTP. Please try again.")

    try:
        result = await register_user(email)
        await log_activity(email, "otp_verified", {"purpose": "register"})
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ---------------------------------------------------------------------------
# Step 1: Send OTP for login
# ---------------------------------------------------------------------------
@router.post("/users/login", response_model=OtpSentResponse)
async def user_login(req: EmailRequest):
    email = _clean_email(req.email)
    # Check if registered
    try:
        await validate_user(email)
    except ValueError:
        raise HTTPException(status_code=404, detail="Email not registered. Please register first.")

    try:
        await generate_and_send_otp(email, "login")
        await log_activity(email, "otp_sent", {"purpose": "login"})
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to send OTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again.")

    return OtpSentResponse(message="OTP sent to your email.", email=email)


# ---------------------------------------------------------------------------
# Step 2: Verify OTP and complete login
# ---------------------------------------------------------------------------
@router.post("/users/verify-login", response_model=LoginResponse)
async def user_verify_login(req: OtpVerifyRequest):
    email = _clean_email(req.email)
    otp = req.otp.strip()

    if not verify_otp(email, otp):
        await log_activity(email, "otp_failed", {"purpose": "login"})
        raise HTTPException(status_code=400, detail="Invalid or expired OTP. Please try again.")

    try:
        result = await validate_user(email)
        await log_activity(email, "login", {"purpose": "login"})
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Usage (unchanged)
# ---------------------------------------------------------------------------
@router.get("/users/usage", response_model=UsageResponse)
async def user_usage(email: str):
    email = _clean_email(email)
    try:
        result = await get_usage(email)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
