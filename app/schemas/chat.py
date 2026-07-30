from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatTurnResponse(BaseModel):
    turn_id: UUID
    role: Literal["assistant"] = "assistant"
    content: str | None
    status: Literal["completed", "failed"]
    created_at: datetime


class ChatHistoryItem(BaseModel):
    turn_id: UUID
    user_content: str | None
    assistant_content: str | None
    status: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    conversation_id: UUID
    messages: list[ChatHistoryItem]
