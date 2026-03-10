from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGODB_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "intelli_credit"
    SECRET_KEY: str = "your-256-bit-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    UPLOAD_DIR: str = "./data/raw_uploads"
    PROCESSED_DIR: str = "./data/processed"
    OCR_GPU_ENABLED: bool = False
    GST_BANK_INFLATION_THRESHOLD: float = 1.4
    ITC_INFLATION_THRESHOLD: float = 1.05
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
