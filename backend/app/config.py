from decimal import Decimal
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    ENVIRONMENT: str = "development"  # development | staging | production
    BOT_TOKEN: str
    DATABASE_URL: str
    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_EXPIRE_DAYS: int = 14

    # --- Access control ---
    # Comma-separated Telegram user IDs allowed to hit /admin/*
    ADMIN_TELEGRAM_IDS: str = ""
    OWNER_TELEGRAM_ID: int = 0

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g. https://your-miniapp.example.com
    CORS_ORIGINS: str = ""

    # --- Revenue / payouts ---
    USER_REVENUE_SHARE: Decimal = Decimal("0.90")
    MIN_WITHDRAWAL_AMOUNT: Decimal = Decimal("1.00")
    MAX_WITHDRAWAL_AMOUNT: Decimal = Decimal("10000.00")

    # --- Telegram webhook ---
    # Set via setWebhook(secret_token=...) and verified on every incoming update.
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # --- Postback / offerwall integration (generic, provider-agnostic) ---
    # Shared secret used to verify HMAC-SHA256 signatures on inbound postbacks.
    POSTBACK_SECRET: str = ""
    # If set, only these source IPs (comma-separated) may call the postback endpoint.
    POSTBACK_IP_ALLOWLIST: str = ""

    # --- Rate limiting ---
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_WITHDRAW: str = "5/minute"
    RATE_LIMIT_POSTBACK: str = "60/minute"
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    SENTRY_DSN: str | None = None

    @field_validator("USER_REVENUE_SHARE")
    @classmethod
    def _validate_share(cls, v: Decimal) -> Decimal:
        if not (Decimal("0") < v <= Decimal("1")):
            raise ValueError("USER_REVENUE_SHARE must be between 0 and 1")
        return v

    @property
    def admin_ids(self) -> set[int]:
        ids = {i.strip() for i in self.ADMIN_TELEGRAM_IDS.split(",") if i.strip()}
        result = {int(i) for i in ids}
        if self.OWNER_TELEGRAM_ID:
            result.add(self.OWNER_TELEGRAM_ID)
        return result

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def postback_ip_allowlist(self) -> set[str]:
        return {ip.strip() for ip in self.POSTBACK_IP_ALLOWLIST.split(",") if ip.strip()}

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
