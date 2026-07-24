from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_analysis_service
from app.api.errors import AnalysisNotFoundError
from app.schemas.analysis_input import (
    CashFlowResponse,
    CashFlowUpdate,
    FinancialGoalsResponse,
    FinancialGoalsUpdate,
)
from app.schemas.analysis import AnalysisDetail, AnalysisSummary
from app.services.analysis import AnalysisService


router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post(
    "",
    response_model=AnalysisSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_analysis(
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisSummary:
    return await service.create()


@router.patch("/{analysis_id}/cash-flow", response_model=CashFlowResponse)
async def update_cash_flow(
    analysis_id: UUID,
    payload: CashFlowUpdate,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> CashFlowResponse:
    result = await service.update_cash_flow(analysis_id, payload)
    if result is None:
        raise AnalysisNotFoundError
    return result


@router.patch(
    "/{analysis_id}/financial-goals",
    response_model=FinancialGoalsResponse,
)
async def update_financial_goals(
    analysis_id: UUID,
    payload: FinancialGoalsUpdate,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> FinancialGoalsResponse:
    result = await service.update_financial_goals(analysis_id, payload)
    if result is None:
        raise AnalysisNotFoundError
    return result


@router.get("/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(
    analysis_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> AnalysisDetail:
    analysis = await service.get(analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError
    return analysis


@router.delete(
    "/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_analysis(
    analysis_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> Response:
    deleted = await service.delete(analysis_id)
    if not deleted:
        raise AnalysisNotFoundError
    return Response(status_code=status.HTTP_204_NO_CONTENT)
