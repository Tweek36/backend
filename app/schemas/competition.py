from uuid import UUID
from pydantic import BaseModel
from app.utils.pagination import PaginatedResponse


class NewCompetitionSchema(BaseModel):
    user_id: UUID
    title: str
    description: str
    category: str
    image: str
    published: bool


class CompetitionSchema(NewCompetitionSchema):
    id: UUID


class CompetitionPaginatedResponseSchema(PaginatedResponse):
    data: list[CompetitionSchema]

