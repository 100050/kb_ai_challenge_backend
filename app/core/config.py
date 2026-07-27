from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    max_housing_plans: int = 10

    database_url: str

    ai_provider: str = "openai"
    ai_model: str | None = None
    ai_api_key: SecretStr | None = None

    data_go_kr_api_key: SecretStr | None = None
    r_one_api_key: SecretStr | None = None
    real_estate_api_timeout_seconds: float = 5.0
    real_estate_lookback_months: int = 12
    comparable_area_tolerance_percent: float = 10.0

    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
