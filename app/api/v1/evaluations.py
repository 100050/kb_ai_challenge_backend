import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_evaluation_service
from app.api.errors import (
    AnalysisNotFoundError,
    AnalysisNotReadyError,
    EvaluationNotFoundError,
)
from app.schemas.evaluation import (
    EvaluationStarted,
    EvaluationStatus,
    FinancialEvaluationResult,
)
from app.services.evaluation import AnalysisNotReady, EvaluationService


router = APIRouter(prefix="/analyses/{analysis_id}", tags=["evaluations"])


@router.post(
    "/evaluation",
    response_model=EvaluationStarted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def evaluate_analysis(
    analysis_id: UUID,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationStarted:
    try:
        result = await service.evaluate(analysis_id)
    except AnalysisNotReady as exc:
        raise AnalysisNotReadyError(exc.details) from exc
    if result is None:
        raise AnalysisNotFoundError
    return result


@router.get("/evaluation", response_model=EvaluationStatus)
async def get_evaluation_status(
    analysis_id: UUID,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> EvaluationStatus:
    result = await service.get_status(analysis_id)
    if result is None:
        raise EvaluationNotFoundError
    return result


@router.get("/result", response_model=FinancialEvaluationResult)
async def get_evaluation_result(
    analysis_id: UUID,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> FinancialEvaluationResult:
    result = await service.get_result(analysis_id)
    if result is None:
        raise EvaluationNotFoundError
    return result


@router.get("/evaluation/events")
async def stream_evaluation_events(
    analysis_id: UUID,
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
) -> StreamingResponse:
    result = await service.get_status(analysis_id)
    if result is None:
        raise EvaluationNotFoundError
    status_result = EvaluationStatus.model_validate(result)

    async def event_stream() -> AsyncIterator[str]:
        data = json.dumps(
            {
                "status": status_result.status,
                "stage": status_result.current_stage,
                "progress": status_result.progress,
            },
            ensure_ascii=False,
        )
        yield f"event: completed\ndata: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )
