from fastapi import APIRouter

from app.api.v1.analyses import router as analyses_router
from app.api.v1.housing_plans import router as housing_plans_router


router = APIRouter()
router.include_router(analyses_router)
router.include_router(housing_plans_router)
