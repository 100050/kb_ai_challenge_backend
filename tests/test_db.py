from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Base, session_factory


def test_database_uses_async_sessions() -> None:
    assert Base.metadata is not None
    assert session_factory.class_ is AsyncSession
    assert session_factory.kw["expire_on_commit"] is False
