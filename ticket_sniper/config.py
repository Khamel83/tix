import sys
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SEATGEEK_CLIENT_ID: str = Field(..., env="SEATGEEK_CLIENT_ID")
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(..., env="TELEGRAM_CHAT_ID")
    ARGUS_BASE_URL: str = Field(..., env="ARGUS_BASE_URL")
    ARGUS_API_KEY: str = Field("", env="ARGUS_API_KEY")
    TZ_DISPLAY: str = Field("America/Los_Angeles", env="TZ_DISPLAY")
    
    TIER2_MAX_REQUESTS_PER_DAY: int = Field(600, env="TIER2_MAX_REQUESTS_PER_DAY")
    GATE_MARGIN: float = Field(0.15, env="GATE_MARGIN")
    DEADMAN_HOURS: int = Field(6, env="DEADMAN_HOURS")
    DATABASE_PATH: str = Field("/data/tickets.sqlite3", env="DATABASE_PATH")
    TARGET_SPORTS_VENUES: List[str] = Field(
        default_factory=lambda: [
            "Dodger Stadium",
            "Crypto.com Arena",
            "Intuit Dome",
        ],
        env="TARGET_SPORTS_VENUES",
    )
    
    ALERT_COALESCE_SECONDS: int = 30
    SUSPICIOUS_EMPTY_FLOOR: int = 5
    CAPTURE_DIR_MAX_MB: int = 500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        sys.stderr.write(f"CRITICAL: Configuration validation failed: {e}\n")
        sys.exit(1)

settings = get_settings()
