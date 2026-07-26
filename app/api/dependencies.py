from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.core.config import settings
from app.repositories.analysis import AnalysisRepository
from app.repositories.evaluation import EvaluationRepository
from app.repositories.housing_plan import HousingPlanRepository
from app.services.analysis import AnalysisService
from app.services.evaluation import EvaluationService


def get_analysis_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisService:
    return AnalysisService(
        AnalysisRepository(session),
        HousingPlanRepository(session),
        EvaluationRepository(session),
        max_housing_plans=settings.max_housing_plans,
    )


def get_evaluation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EvaluationService:
    return EvaluationService(
        AnalysisRepository(session),
        HousingPlanRepository(session),
        EvaluationRepository(session),
    )
