from uuid import UUID

from app.repositories.analysis import AnalysisRepository
from app.schemas.analysis import AnalysisDetail, AnalysisSummary


class AnalysisService:
    def __init__(self, repository: AnalysisRepository) -> None:
        self.repository = repository

    async def create(self) -> AnalysisSummary:
        analysis = await self.repository.create()
        return AnalysisSummary(
            analysis_id=analysis.id,
            status=analysis.status,
            current_step=analysis.current_step,
            progress=analysis.progress,
            created_at=analysis.created_at,
        )

    async def get(self, analysis_id: UUID) -> AnalysisDetail | None:
        analysis = await self.repository.get(analysis_id)
        if analysis is None:
            return None

        return AnalysisDetail(
            analysis_id=analysis.id,
            status=analysis.status,
            current_step=analysis.current_step,
            progress=analysis.progress,
            properties=None,
            cash_flow=None,
            financial_goals=None,
            loan_plan=None,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )

    async def delete(self, analysis_id: UUID) -> bool:
        return await self.repository.delete(analysis_id)
