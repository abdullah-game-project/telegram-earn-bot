from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30
    OWNER_TELEGRAM_ID: int = 0          # set your Telegram ID later
    ENVIRONMENT: str = "production"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()