from uuid import uuid4

import pytest
from sqlalchemy import inspect

from app.repositories.conversation import ConversationRepository


class FakeSession:
    def __init__(self) -> None:
        self.added = None

    async def scalar(self, statement):
        return None

    def add(self, instance) -> None:
        self.added = instance

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_get_or_create_initializes_turns_as_loaded_empty_collection(
) -> None:
    session = FakeSession()
    repository = ConversationRepository(session)  # type: ignore[arg-type]

    conversation = await repository.get_or_create(uuid4())

    assert inspect(conversation).attrs.turns.loaded_value == []
