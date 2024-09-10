from uuid import UUID
from pydantic import BaseModel
from app.utils.pagination import PaginatedResponse
from typing import Optional


class CompetitionResponseSchema(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str
    category: str
    image: str
    published: bool


class CompetitionPaginatedResponseSchema(PaginatedResponse):
    data: list[CompetitionResponseSchema]

class IdPayloadSchema(BaseModel):
    id: UUID

class CompetitionItemResponseSchema(BaseModel):
    id: UUID
    title: str
    description: str
    videoId: str


class CreateCompetitionItemPayloadSchema(BaseModel):
    title: str
    description: str
    videoId: str


class UpdateCompetitionItemPayloadSchema(BaseModel):
    title: Optional[str]
    description: Optional[str]
    videoId: Optional[str]
