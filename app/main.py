from fastapi import APIRouter, FastAPI

from app.core.config import settings


api_v1_router = APIRouter(prefix=settings.api_v1_prefix)


@api_v1_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(
    title="KB Housing AI API",
)

app.include_router(api_v1_router)
