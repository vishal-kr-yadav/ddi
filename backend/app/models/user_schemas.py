from pydantic import BaseModel
from typing import Optional


class EmailRequest(BaseModel):
    email: str


class RegisterResponse(BaseModel):
    email: str
    registered_at: str
    checks_remaining: int
    message: str


class LoginResponse(BaseModel):
    email: str
    registered_at: str
    checks_used: int
    checks_remaining: int
    resets_at: Optional[str] = None


class UsageResponse(BaseModel):
    email: str
    checks_used: int
    checks_remaining: int
    resets_at: Optional[str] = None


class OtpVerifyRequest(BaseModel):
    email: str
    otp: str


class OtpSentResponse(BaseModel):
    message: str
    email: str
