from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Bar Vision API"
    app_version: str = "0.1.0"
    environment: str = "development"

    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(validation_alias="DATABASE_URL")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 14

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
