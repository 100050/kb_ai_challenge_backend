from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import Settings


def create_ai_model(settings: Settings) -> Model:
    if settings.ai_provider != "openai":
        raise ValueError(f"지원하지 않는 AI provider: {settings.ai_provider}")
    if settings.ai_model is None:
        raise ValueError("AI_MODEL 환경변수가 필요합니다.")
    if settings.ai_api_key is None:
        raise ValueError("AI_API_KEY 환경변수가 필요합니다.")

    return OpenAIResponsesModel(
        settings.ai_model,
        provider=OpenAIProvider(
            api_key=settings.ai_api_key.get_secret_value(),
        ),
    )
