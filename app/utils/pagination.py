from typing import Any, Generic, Sequence, Tuple, TypeVar
from pydantic import BaseModel
from sqlalchemy.sql.selectable import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

_T = TypeVar("_T", bound=Any)


class PaginatedResponse(BaseModel, Generic[_T]):
    data: Sequence[_T]
    max_per_page: int
    page: int
    total: int


class Paginator(Generic[_T]):
    data: Sequence[_T]

    def __init__(
        self,
        session: AsyncSession,
        stmt: Select[Tuple[_T]],
        max_per_page: int = 10,
        page: int = 1,
    ) -> None:
        self._session = session
        self._stmt = stmt
        self._max_per_page = max_per_page
        self._page = page
        self._to_update = True
        self._total: int = None

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value: int):
        self._to_update = True
        self._page = value

    @property
    def max_per_page(self):
        return self._max_per_page

    @max_per_page.setter
    def max_per_page(self, value: int):
        self._to_update = True
        self._max_per_page = value

    @property
    def count_stmt(self):
        return select(func.count()).select_from(self._stmt)

    @property
    def paginated_stmt(self):
        offset = (self._page - 1) * self._max_per_page
        return self._stmt.offset(offset).limit(self._max_per_page)

    @property
    def total(self):
        if not self._total:
            return 0
        return self._total

    async def execute(self):
        self._total = await self._session.scalar(self.count_stmt)
        scalars = await self._session.stream_scalars(self.paginated_stmt)
        self.data = await scalars.all()
        self._to_update = False

    @property
    def response(self):
        if self._to_update:
            raise ValueError(
                "Data needs to be updated. Call execute() before accessing the response."
            )
        return PaginatedResponse(
            data=self.data,
            max_per_page=self.max_per_page,
            page=self.page,
            total=self.total,
        )
