from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    # Required (but default empty so app can at least start for health checks)
    ANTHROPIC_API_KEY: str = ""

    @field_validator("ANTHROPIC_API_KEY", "MONGO_URI", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if isinstance(v, str) else v

    # Optional news source API keys
    NEWSAPI_KEY: Optional[str] = None
    GUARDIAN_API_KEY: Optional[str] = None
    NYT_API_KEY: Optional[str] = None
    GNEWS_API_KEY: Optional[str] = None
    CURRENTS_API_KEY: Optional[str] = None
    MEDIASTACK_API_KEY: Optional[str] = None
    BING_NEWS_API_KEY: Optional[str] = None

    # MongoDB
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "ddi"

    # App config
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
        "http://localhost:5176", "http://localhost:5177", "http://localhost:3000",
        "https://ddi-production.up.railway.app",
    ]
    MAX_ARTICLES_PER_SOURCE: int = 5
    TOP_ARTICLES_FOR_ANALYSIS: int = 10
    DAILY_DEVICE_LIMIT: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
