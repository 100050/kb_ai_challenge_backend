from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_analysis_service
from app.api.errors import (
    AnalysisNotFoundError,
    HousingPlanLimitReachedError,
    HousingPlanNotFoundError,
)
from app.schemas.housing_plan import (
    HousingPlanCreate,
    HousingPlanListResponse,
    HousingPlanResponse,
    HousingPlanUpdate,
)
from app.services.analysis import AnalysisService, HousingPlanLimitReached


router = APIRouter(
    prefix="/analyses/{analysis_id}/housing-plans",
    tags=["housing-plans"],
)


@router.post(
    "",
    response_model=HousingPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_housing_plan(
    analysis_id: UUID,
    payload: HousingPlanCreate,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> HousingPlanResponse:
    try:
        result = await service.create_housing_plan(analysis_id, payload)
    except HousingPlanLimitReached as exc:
        raise HousingPlanLimitReachedError from exc
    if result is None:
        raise AnalysisNotFoundError
    return result


@router.get("", response_model=HousingPlanListResponse)
async def list_housing_plans(
    analysis_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> HousingPlanListResponse:
    result = await service.list_housing_plans(analysis_id)
    if result is None:
        raise AnalysisNotFoundError
    return HousingPlanListResponse(housing_plans=result)


@router.get("/{property_id}", response_model=HousingPlanResponse)
async def get_housing_plan(
    analysis_id: UUID,
    property_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> HousingPlanResponse:
    result = await service.get_housing_plan(analysis_id, property_id)
    if result is None:
        raise HousingPlanNotFoundError
    return result


@router.patch("/{property_id}", response_model=HousingPlanResponse)
async def update_housing_plan(
    analysis_id: UUID,
    property_id: UUID,
    payload: HousingPlanUpdate,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> HousingPlanResponse:
    result = await service.update_housing_plan(
        analysis_id,
        property_id,
        payload,
    )
    if result is None:
        raise HousingPlanNotFoundError
    return result


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_housing_plan(
    analysis_id: UUID,
    property_id: UUID,
    service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> Response:
    deleted = await service.delete_housing_plan(analysis_id, property_id)
    if not deleted:
        raise HousingPlanNotFoundError
    return Response(status_code=status.HTTP_204_NO_CONTENT)
