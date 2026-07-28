from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import ChatTurn, Conversation


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_analysis(
        self,
        analysis_id: UUID,
    ) -> Conversation | None:
        return await self.session.scalar(
            select(Conversation)
            .where(Conversation.analysis_id == analysis_id)
            .options(selectinload(Conversation.turns)),
        )

    async def get_or_create(self, analysis_id: UUID) -> Conversation:
        conversation = await self.get_by_analysis(analysis_id)
        if conversation is not None:
            return conversation

        conversation = Conversation(analysis_id=analysis_id)
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def add_turn(self, turn: ChatTurn) -> ChatTurn:
        self.session.add(turn)
        await self.session.commit()
        await self.session.refresh(turn)
        return turn

    async def get_turn(
        self,
        conversation_id: UUID,
        turn_id: UUID,
    ) -> ChatTurn | None:
        return await self.session.scalar(
            select(ChatTurn).where(
                ChatTurn.id == turn_id,
                ChatTurn.conversation_id == conversation_id,
            ),
        )

    async def save_turn(self, turn: ChatTurn) -> ChatTurn:
        await self.session.commit()
        await self.session.refresh(turn)
        return turn

    async def clear(self, conversation_id: UUID) -> None:
        await self.session.execute(
            delete(ChatTurn).where(
                ChatTurn.conversation_id == conversation_id,
            ),
        )
        await self.session.commit()
