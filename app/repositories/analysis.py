from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self) -> Analysis:
        analysis = Analysis()
        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def get(self, analysis_id: UUID) -> Analysis | None:
        return await self.session.get(Analysis, analysis_id)

    async def delete(self, analysis_id: UUID) -> bool:
        analysis = await self.get(analysis_id)
        if analysis is None:
            return False

        await self.session.delete(analysis)
        await self.session.commit()
        return True
