from app.core.config import Settings


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:password@localhost/test",
        _env_file=None,
    )

    assert settings.app_env == "local"
    assert settings.log_level == "INFO"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.max_housing_plans == 10
    assert settings.ai_provider == "openai"
    assert settings.ai_model is None
    assert settings.ai_api_key is None
    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
