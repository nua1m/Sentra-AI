from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # API security
    sentra_api_key: str

    # Agent0 connection (internal Docker network)
    agent0_internal_url: str = "http://agent0:80"
    agent0_api_key: str = ""

    # Database
    database_url: str

    # Service config
    scan_timeout_seconds: int = 600   # 10 min max for a full audit
    json_extract_timeout: int = 180   # JSON extraction can be slower on remote models
    quick_scan_timeout_seconds: int = 180
    stale_scan_timeout_seconds: int = 1800
    debug: bool = False

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
