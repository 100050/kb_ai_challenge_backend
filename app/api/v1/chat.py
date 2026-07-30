import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_service
from app.api.errors import AnalysisNotFoundError
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageCreate,
)
from app.services.chat import ChatService


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
        if result.content:
            yield _sse(
                "message_delta",
                {"content": result.content},
            )
        yield _sse("message_end", result.model_dump(mode="json"))

    return StreamingResponse(events(), media_type="text/event-stream")

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
