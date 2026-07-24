from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories.analysis import AnalysisRepository
from app.services.analysis import AnalysisService


def get_analysis_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AnalysisService:
    return AnalysisService(AnalysisRepository(session))
