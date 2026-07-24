from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.errors import (
    ApiError,
    api_error_handler,
    validation_error_handler,
)
from app.api.v1.router import router as v1_router
from app.core.config import settings


api_v1_router = APIRouter(prefix=settings.api_v1_prefix)
api_v1_router.include_router(v1_router)


@api_v1_router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app = FastAPI(
    title="KB Housing AI API",
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.include_router(api_v1_router)
