import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_service
from app.api.errors import AnalysisNotFoundError, ApiError
from app.schemas.chat import (
    ChatApprovalRequest,
    ChatHistoryResponse,
    ChatMessageCreate,
    ChatTurnResponse,
)
from app.services.chat import (
    ChatService,
    ConversationNotFound,
    PendingApprovalNotFound,
)


router = APIRouter(
    prefix="/analyses/{analysis_id}/chat",
    tags=["chat"],
)


def _sse(event: str, data: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
    )


@router.post("/messages")
async def send_message(
    analysis_id: UUID,
    payload: ChatMessageCreate,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        yield _sse("message_start", {"analysis_id": analysis_id})
        result = await service.send_message(analysis_id, payload.content)
        if result is None:
            yield _sse(
                "error",
                {"code": "ANALYSIS_NOT_FOUND"},
            )
            return
        if result.status == "approval_required":
            yield _sse(
                "approval_required",
                result.model_dump(mode="json"),
            )
        elif result.content:
            yield _sse(
                "message_delta",
                {"content": result.content},
            )
        yield _sse("message_end", result.model_dump(mode="json"))

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/approvals", response_model=ChatTurnResponse)
async def resolve_approval(
    analysis_id: UUID,
    payload: ChatApprovalRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatTurnResponse:
    try:
        return await service.resolve_approval(
            analysis_id,
            payload.turn_id,
            payload.tool_call_id,
            approved=payload.approved,
        )
    except ConversationNotFound as exc:
        raise AnalysisNotFoundError from exc
    except PendingApprovalNotFound as exc:
        raise ApiError(
            status_code=404,
            code="PENDING_APPROVAL_NOT_FOUND",
            message="처리할 도구 승인 요청을 찾을 수 없습니다.",
        ) from exc


@router.get("/messages", response_model=ChatHistoryResponse)
async def get_messages(
    analysis_id: UUID,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatHistoryResponse:
    result = await service.history(analysis_id)
    if result is None:
        raise AnalysisNotFoundError
    return result


@router.delete("/messages", status_code=status.HTTP_204_NO_CONTENT)
async def clear_messages(
    analysis_id: UUID,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> Response:
    if not await service.clear(analysis_id):
        raise AnalysisNotFoundError
    return Response(status_code=status.HTTP_204_NO_CONTENT)
