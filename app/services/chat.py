from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from pydantic_ai import (
    Agent,
    DeferredToolRequests,
    DeferredToolResults,
    ModelMessagesTypeAdapter,
    ToolDenied,
)

from app.ai.dependencies import ChatDependencies
from app.models.conversation import ChatTurn
from app.repositories.conversation import ConversationRepository
from app.repositories.evaluation import EvaluationRepository
from app.schemas.chat import (
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatTurnResponse,
    PendingToolApproval,
)
from app.services.analysis import AnalysisService


class ConversationNotFound(Exception):
    pass


class PendingApprovalNotFound(Exception):
    pass


class ChatService:
    def __init__(
        self,
        repository: ConversationRepository,
        evaluation_repository: EvaluationRepository,
        analysis_service: AnalysisService,
        agent: Agent[ChatDependencies, str | DeferredToolRequests],
    ) -> None:
        self.repository = repository
        self.evaluation_repository = evaluation_repository
        self.analysis_service = analysis_service
        self.agent = agent

    async def send_message(
        self,
        analysis_id: UUID,
        content: str,
    ) -> ChatTurnResponse | None:
        deps = await self._dependencies(analysis_id)
        if deps is None:
            return None
        conversation = await self.repository.get_or_create(analysis_id)
        history = self._history(conversation.turns)

        result = await self.agent.run(
            content,
            deps=deps,
            message_history=history,
            conversation_id=str(conversation.id),
        )
        messages = self._dump_messages(result.new_messages())

        if isinstance(result.output, DeferredToolRequests):
            approvals = [
                {
                    "tool_call_id": call.tool_call_id,
                    "tool_name": call.tool_name,
                    "arguments": call.args_as_dict(),
                }
                for call in result.output.approvals
            ]
            turn = ChatTurn(
                conversation_id=conversation.id,
                user_content=content,
                assistant_content=None,
                status="approval_required",
                model_messages=messages,
                pending_approvals=approvals,
            )
        else:
            turn = ChatTurn(
                conversation_id=conversation.id,
                user_content=content,
                assistant_content=result.output,
                status="completed",
                model_messages=messages,
                pending_approvals=None,
            )

        await self.repository.add_turn(turn)
        return self._turn_response(turn)

    async def resolve_approval(
        self,
        analysis_id: UUID,
        turn_id: UUID,
        tool_call_id: str,
        *,
        approved: bool,
    ) -> ChatTurnResponse:
        deps = await self._dependencies(analysis_id)
        if deps is None:
            raise ConversationNotFound
        conversation = await self.repository.get_by_analysis(analysis_id)
        if conversation is None:
            raise ConversationNotFound
        turn = await self.repository.get_turn(conversation.id, turn_id)
        if turn is None or turn.status != "approval_required":
            raise PendingApprovalNotFound

        pending_ids = {
            item["tool_call_id"] for item in turn.pending_approvals or []
        }
        if tool_call_id not in pending_ids:
            raise PendingApprovalNotFound

        decision: bool | ToolDenied = (
            True
            if approved
            else ToolDenied("사용자가 입력 변경을 취소했습니다.")
        )
        history = self._history(conversation.turns)
        result = await self.agent.run(
            deps=deps,
            message_history=history,
            conversation_id=str(conversation.id),
            deferred_tool_results=DeferredToolResults(
                approvals={tool_call_id: decision},
            ),
        )
        turn.model_messages = [
            *turn.model_messages,
            *self._dump_messages(result.new_messages()),
        ]

        if isinstance(result.output, DeferredToolRequests):
            approvals = [
                {
                    "tool_call_id": call.tool_call_id,
                    "tool_name": call.tool_name,
                    "arguments": call.args_as_dict(),
                }
                for call in result.output.approvals
            ]
            turn.status = "approval_required"
            turn.pending_approvals = approvals
            turn.assistant_content = None
        else:
            turn.status = "completed"
            turn.pending_approvals = None
            turn.assistant_content = result.output

        await self.repository.save_turn(turn)
        return self._turn_response(turn)

    async def history(
        self,
        analysis_id: UUID,
    ) -> ChatHistoryResponse | None:
        conversation = await self.repository.get_by_analysis(analysis_id)
        if conversation is None:
            analysis = await self.analysis_service.get(analysis_id)
            if analysis is None:
                return None
            conversation = await self.repository.get_or_create(analysis_id)

        return ChatHistoryResponse(
            conversation_id=conversation.id,
            messages=[
                ChatHistoryItem(
                    turn_id=turn.id,
                    user_content=turn.user_content,
                    assistant_content=turn.assistant_content,
                    status=turn.status,
                    created_at=turn.created_at,
                )
                for turn in conversation.turns
            ],
        )

    async def clear(self, analysis_id: UUID) -> bool:
        conversation = await self.repository.get_by_analysis(analysis_id)
        if conversation is None:
            return await self.analysis_service.get(analysis_id) is not None
        await self.repository.clear(conversation.id)
        return True

    async def _dependencies(
        self,
        analysis_id: UUID,
    ) -> ChatDependencies | None:
        analysis = await self.analysis_service.get(analysis_id)
        if analysis is None:
            return None
        evaluation = await self.evaluation_repository.get(analysis_id)
        return ChatDependencies(
            analysis_id=analysis_id,
            analysis_service=self.analysis_service,
            analysis_context={
                "analysis": analysis.model_dump(mode="json"),
                "evaluation": (
                    evaluation.result
                    if evaluation is not None
                    else None
                ),
            },
        )

    @staticmethod
    def _history(turns: list[ChatTurn]) -> list[Any]:
        raw_messages = [
            message
            for turn in turns
            for message in turn.model_messages
        ]
        return ModelMessagesTypeAdapter.validate_python(raw_messages)

    @staticmethod
    def _dump_messages(messages: list[Any]) -> list[dict[str, Any]]:
        dumped = ModelMessagesTypeAdapter.dump_python(
            messages,
            mode="json",
        )
        return TypeAdapter(list[dict[str, Any]]).validate_python(dumped)

    @staticmethod
    def _turn_response(turn: ChatTurn) -> ChatTurnResponse:
        return ChatTurnResponse(
            turn_id=turn.id,
            content=turn.assistant_content,
            status=turn.status,
            pending_approvals=[
                PendingToolApproval.model_validate(item)
                for item in turn.pending_approvals or []
            ],
            created_at=turn.created_at,
        )
