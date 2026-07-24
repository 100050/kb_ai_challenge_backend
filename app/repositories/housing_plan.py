from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.housing_plan import HousingPlan


class HousingPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, analysis_id: UUID) -> HousingPlan:
        housing_plan = HousingPlan(analysis_id=analysis_id)
        self.session.add(housing_plan)
        await self.session.flush()
        return housing_plan

    async def list(self, analysis_id: UUID) -> list[HousingPlan]:
        result = await self.session.scalars(
            select(HousingPlan)
            .where(HousingPlan.analysis_id == analysis_id)
            .order_by(HousingPlan.created_at, HousingPlan.id),
        )
        return list(result)

    async def get(
        self,
        analysis_id: UUID,
        property_id: UUID,
    ) -> HousingPlan | None:
        return await self.session.scalar(
            select(HousingPlan).where(
                HousingPlan.id == property_id,
                HousingPlan.analysis_id == analysis_id,
            ),
        )

    async def delete(self, housing_plan: HousingPlan) -> None:
        await self.session.delete(housing_plan)
        await self.session.flush()
