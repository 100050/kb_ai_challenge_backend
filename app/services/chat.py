import json
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from pydantic_ai import (
    Agent,
    ModelMessagesTypeAdapter,
)
from pydantic_ai.messages import ModelRequest, SystemPromptPart

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
from app.services.evaluation import EvaluationService


class ChatService:
    def __init__(
        self,
        repository: ConversationRepository,
        evaluation_repository: EvaluationRepository,
        analysis_service: AnalysisService,
        evaluation_service: EvaluationService,
        agent: Agent[ChatDependencies, str],
    ) -> None:
        self.repository = repository
        self.evaluation_repository = evaluation_repository
        self.analysis_service = analysis_service
        self.evaluation_service = evaluation_service
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
        current_snapshot = self._input_snapshot(deps.analysis_context)
        context_messages: list[Any] = []
        if conversation.analysis_snapshot is not None:
            changes = self._context_changes(
                conversation.analysis_snapshot,
                current_snapshot,
            )
            if changes:
                context_messages.append(self._context_change_message(changes))
        history = [
            *self._history(conversation.turns),
            *context_messages,
        ]

        result = await self.agent.run(
            content,
            deps=deps,
            message_history=history,
            conversation_id=str(conversation.id),
        )
        messages = self._dump_messages(
            [
                *context_messages,
                *result.new_messages(),
            ],
        )

        turn = ChatTurn(
            conversation_id=conversation.id,
            user_content=content,
            assistant_content=result.output,
            status="completed",
            model_messages=messages,
            pending_approvals=None,
        )

        refreshed_deps = await self._dependencies(analysis_id)
        if refreshed_deps is not None:
            conversation.analysis_snapshot = self._input_snapshot(
                refreshed_deps.analysis_context,
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
        housing_plans = []
        for summary in analysis.housing_plans:
            housing_plan = await self.analysis_service.get_housing_plan(
                analysis_id,
                summary.property_id,
            )
            if housing_plan is not None:
                housing_plans.append(
                    housing_plan.model_dump(mode="json"),
                )
        analysis_payload = analysis.model_dump(mode="json")
        analysis_payload["housing_plans"] = housing_plans
        return ChatDependencies(
            analysis_id=analysis_id,
            analysis_service=self.analysis_service,
            evaluation_service=self.evaluation_service,
            analysis_context={
                "analysis": analysis_payload,
                "evaluation": (
                    evaluation.result
                    if evaluation is not None
                    else None
                ),
            },
        )

    @staticmethod
    def _input_snapshot(
        analysis_context: dict[str, Any],
    ) -> dict[str, Any]:
        analysis = analysis_context["analysis"]
        excluded_housing_fields = {
            "analysis_id",
            "legal_dong_code",
            "is_complete",
            "created_at",
            "updated_at",
        }
        return {
            "cash_flow": analysis.get("cash_flow"),
            "financial_goals": analysis.get("financial_goals"),
            "housing_plans": [
                {
                    key: value
                    for key, value in housing_plan.items()
                    if key not in excluded_housing_fields
                }
                for housing_plan in analysis.get("housing_plans", [])
            ],
        }

    @classmethod
    def _context_changes(
        cls,
        previous: Any,
        current: Any,
        path: str = "",
    ) -> list[dict[str, Any]]:
        if previous == current:
            return []
        if isinstance(previous, dict) and isinstance(current, dict):
            changes = []
            for key in sorted(previous.keys() | current.keys()):
                child_path = f"{path}.{key}" if path else key
                changes.extend(
                    cls._context_changes(
                        previous.get(key),
                        current.get(key),
                        child_path,
                    ),
                )
            return changes
        if (
            path == "housing_plans"
            and isinstance(previous, list)
            and isinstance(current, list)
        ):
            previous_by_id = {
                str(item["property_id"]): item for item in previous
            }
            current_by_id = {
                str(item["property_id"]): item for item in current
            }
            changes = []
            for property_id in sorted(
                previous_by_id.keys() | current_by_id.keys(),
            ):
                plan_path = f"housing_plans[{property_id}]"
                changes.extend(
                    cls._context_changes(
                        previous_by_id.get(property_id),
                        current_by_id.get(property_id),
                        plan_path,
                    ),
                )
            return changes
        return [
            {
                "path": path,
                "before": previous,
                "after": current,
            },
        ]

    @staticmethod
    def _context_change_message(
        changes: list[dict[str, Any]],
    ) -> ModelRequest:
        return ModelRequest(
            parts=[
                SystemPromptPart(
                    content=(
                        "이전 대화 이후 분석 입력값이 변경되었습니다. "
                        "이전 값보다 아래 최신 변경값을 우선하여 답변하세요.\n"
                        + json.dumps(
                            changes,
                            ensure_ascii=False,
                            default=str,
                        )
                    ),
                ),
            ],
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
