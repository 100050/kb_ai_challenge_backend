from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatApprovalRequest(BaseModel):
    turn_id: UUID
    tool_call_id: str
    approved: bool


class PendingToolApproval(BaseModel):
    tool_call_id: str
    tool_name: str
    arguments: dict


class ChatTurnResponse(BaseModel):
    turn_id: UUID
    role: Literal["assistant"] = "assistant"
    content: str | None
    status: Literal["completed", "approval_required", "failed"]
    pending_approvals: list[PendingToolApproval] = Field(
        default_factory=list,
    )
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
