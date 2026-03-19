from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Browser behaviour
    browser_timeout_ms: int = 30_000
    page_load_wait_ms: int = 5_000
    headless: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # HTTP client
    http_timeout_s: float = 15.0
    http_max_retries: int = 3
    http_concurrency: int = 5
    rate_limit_delay_s: float = 0.5

    # Storage
    db_path: str = "retailer_checker.db"
    output_dir: str = "./output"

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Optional proxy
    http_proxy: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AC_")


settings = Config()
