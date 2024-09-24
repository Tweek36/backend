from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.utils.pagination import PaginatedResponse


class NewCompetitionItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    title: str
    description: str
    videoId: str


class CompetitionItemSchema(NewCompetitionItemSchema):
    id: UUID


class CompetitionItemPaginatedResponseSchema(PaginatedResponse):
    data: list[CompetitionItemSchema]


class UpdateCompetitionItemPayloadSchema(BaseModel):
    title: str | None = None
    description: str | None = None
    videoId: str | None = None
