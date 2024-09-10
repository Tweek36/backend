from uuid import UUID

from sqlalchemy import select
from app.services import BaseService, ModelRequests
from app.models.tests import Competition, User
from app.utils.pagination import Paginator
from app.utils.token import AccessToken


class UserService(BaseService, ModelRequests[User]):
    model = User

    async def me(self, authorization: AccessToken):
        user = await self.get(id=authorization.sub)
        return user

    async def get_competitions(
        self, user_id: UUID, published: bool | None, max_per_page: int, page: int
    ):
        stmt = select(Competition).filter(Competition.user_id == user_id)
        if published is not None:
            stmt = stmt.filter(Competition.published == True)  # noqa: E712
        paginator = Paginator(
            stmt=stmt, session=self.session, max_per_page=max_per_page, page=page
        )
        await paginator.execute()
        return paginator.response
