from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from app.services import BaseService, ModelRequests
from app.models.tests import Competition, CompetitionItem


class CompetitionItemService(BaseService, ModelRequests[CompetitionItem]):
    model = CompetitionItem

    async def get_list(self, **filters):
        competition_id: UUID = filters.get("competition_id")
        if competition_id:
            competition = await self.session.scalar(
                select(Competition).filter(Competition.id == competition_id)
            )
            if not competition or (
                competition.published and competition.user_id != self.token.sub
            ):
                raise HTTPException(404, "Competition not found")
        return await super().get_list(**filters)

    async def get_paginated_list(self, max_per_page: int, page: int, **filters):
        competition_id: UUID = filters.get("competition_id")
        if competition_id:
            competition = await self.session.scalar(
                select(Competition).filter(Competition.id == competition_id)
            )
            if not competition or (
                competition.published and competition.user_id != self.token.sub
            ):
                raise HTTPException(404, "Competition not found")
        return await super().get_paginated_list(max_per_page, page, **filters)

    async def get_optional_paginated_list(
        self, max_per_page: int | None, page: int | None, **filters
    ):
        if max_per_page and page:
            return await self.get_paginated_list(
                max_per_page=max_per_page, page=page, **filters
            )
        else:
            return await self.get_list(**filters)

    async def get(self, **filters) -> CompetitionItem:
        competition_id: UUID = filters.get("competition_id")
        if competition_id:
            competition = await self.session.scalar(
                select(Competition).filter(Competition.id == competition_id)
            )
            if not competition or (
                competition.published and competition.user_id != self.token.sub
            ):
                raise HTTPException(404, "Competition not found")
        return await super().get(**filters)

    async def update(self, id: UUID, competition_id: UUID, **data):
        competition = await self.session.scalar(
            select(Competition).filter(Competition.id == competition_id)
        )
        if not competition or (competition.user_id != self.token.sub):
            raise HTTPException(404, "Competition not found")
        return await super().update(id, **data)

    async def delete(self, id: UUID, competition_id: UUID):
        competition = await self.session.scalar(
            select(Competition).filter(Competition.id == competition_id)
        )
        if not competition or (competition.user_id != self.token.sub):
            raise HTTPException(404, "Competition not found")
        return await super().delete(id)
