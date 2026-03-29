import random
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# In-memory OTP store: { email: { otp, expires_at, purpose } }
_otp_store: Dict[str, Dict[str, Any]] = {}

OTP_EXPIRY_MINUTES = 5


def _generate_otp() -> str:
    return str(random.randint(100000, 999999))


def _send_email_sync(to_email: str, otp: str, purpose: str) -> None:
    smtp_email = settings.SMTP_EMAIL
    smtp_password = settings.SMTP_APP_PASSWORD

    if not smtp_email or not smtp_password:
        raise ValueError("SMTP_EMAIL and SMTP_APP_PASSWORD must be set in .env")

    subject = f"DDI - Your verification code: {otp}"
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"DDI Verification <{smtp_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(f"Your DDI verification code is: {otp}\n\nExpires in {OTP_EXPIRY_MINUTES} minutes.", "plain"))
    msg.attach(MIMEText(html, "html"))

    # Try port 587 (STARTTLS) first, fallback to 465 (SSL)
    # Railway and many cloud providers block port 465
    for method in ["starttls", "ssl"]:
        try:
            if method == "starttls":
                server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
                server.ehlo()
                server.starttls()
            else:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)

            with server:
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, to_email, msg.as_string())
            logger.info(f"OTP email sent to {to_email} via {method}")
            return  # success
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP auth failed ({method}): {e}")
            raise ValueError("Email service authentication failed. Check SMTP credentials.")
        except (smtplib.SMTPException, OSError) as e:
            logger.warning(f"SMTP {method} failed: {e}")
            if method == "ssl":
                raise ValueError(f"Failed to send email via both methods: {e}")


async def generate_and_send_otp(email: str, purpose: str) -> None:
    otp = _generate_otp()
    _otp_store[email] = {
        "otp": otp,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "purpose": purpose,
    }
    await asyncio.to_thread(_send_email_sync, email, otp, purpose)


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
