import random
import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory OTP store: { email: { otp, expires_at, purpose } }
_otp_store: Dict[str, Dict[str, Any]] = {}

OTP_EXPIRY_MINUTES = 5

RESEND_API_URL = "https://api.resend.com/emails"


def _generate_otp() -> str:
    return str(random.randint(100000, 999999))


async def _send_email_resend(to_email: str, otp: str, purpose: str) -> None:
    api_key = settings.RESEND_API_KEY
    if not api_key:
        raise ValueError("RESEND_API_KEY must be set")

    action = "register your account" if purpose == "register" else "sign in"

    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; background: linear-gradient(135deg, #3b82f6, #06b6d4);
                        color: white; font-weight: bold; font-size: 14px; padding: 8px 12px;
                        border-radius: 8px; letter-spacing: 1px;">DDI</div>
            <p style="color: #9ca3af; font-size: 12px; margin-top: 8px;">Data Driven Intelligence</p>
        </div>
        <h2 style="color: #1f2937; text-align: center; margin-bottom: 8px;">Verification Code</h2>
        <p style="color: #6b7280; text-align: center; font-size: 14px;">
            Use this code to {action} on DDI:
        </p>
        <div style="background: #f3f4f6; border-radius: 12px; padding: 20px; text-align: center;
                    margin: 24px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1f2937;">
                {otp}
            </span>
        </div>
        <p style="color: #9ca3af; text-align: center; font-size: 12px;">
            This code expires in {OTP_EXPIRY_MINUTES} minutes. Do not share it with anyone.
        </p>
    </div>
    """

    payload = {
        "from": "DDI Verification <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"DDI - Your verification code: {otp}",
        "html": html,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    if resp.status_code >= 400:
        logger.error(f"Resend API error {resp.status_code}: {resp.text}")
        raise ValueError(f"Email send failed: {resp.text}")

    logger.info(f"OTP email sent to {to_email} for {purpose} via Resend")


async def generate_and_send_otp(email: str, purpose: str) -> None:
    otp = _generate_otp()
    _otp_store[email] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "purpose": purpose,
    }
    await _send_email_resend(email, otp, purpose)


def verify_otp(email: str, otp: str) -> bool:
    entry = _otp_store.get(email)
    if not entry:
        return False
    if datetime.now(timezone.utc) > entry["expires_at"]:
        del _otp_store[email]
        return False
    if entry["otp"] != otp:
        return False
    # OTP is valid — remove it so it can't be reused
    del _otp_store[email]
    return True
