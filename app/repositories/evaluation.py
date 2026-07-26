from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation


class EvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, analysis_id: UUID) -> Evaluation | None:
        return await self.session.scalar(
            select(Evaluation).where(
                Evaluation.analysis_id == analysis_id,
            ),
        )

    async def save_completed(
        self,
        analysis_id: UUID,
        result: dict,
    ) -> Evaluation:
        evaluation = await self.get(analysis_id)
        if evaluation is None:
            evaluation = Evaluation(analysis_id=analysis_id)
            self.session.add(evaluation)

        evaluation.status = "completed"
        evaluation.current_stage = "financial_management"
        evaluation.progress = 100
        evaluation.result = result
        evaluation.error = None
        await self.session.commit()
        await self.session.refresh(evaluation)
        return evaluation

    async def delete(self, analysis_id: UUID) -> None:
        evaluation = await self.get(analysis_id)
        if evaluation is not None:
            await self.session.delete(evaluation)
            await self.session.flush()
