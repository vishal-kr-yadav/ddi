from pydantic import BaseModel
from typing import Optional


class DeviceUsageResponse(BaseModel):
    device_id: str
    checks_used: int
    checks_remaining: int
    limit: int
    resets_at: Optional[str] = None
