from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from pydantic_ai import (
    Agent,
    ModelMessagesTypeAdapter,
)

from app.ai.dependencies import ChatDependencies
from app.models.conversation import ChatTurn
from app.repositories.conversation import ConversationRepository
from app.repositories.evaluation import EvaluationRepository
from app.schemas.chat import (
    ChatHistoryItem,
    ChatHistoryResponse,
    ChatTurnResponse,
)
from app.services.analysis import AnalysisService


class ChatService:
    def __init__(
        self,
        repository: ConversationRepository,
        evaluation_repository: EvaluationRepository,
        analysis_service: AnalysisService,
        agent: Agent[ChatDependencies, str],
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
            created_at=turn.created_at,
        )
