from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.utils.pagination import PaginatedResponse


class NewRatingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    competition_id: UUID
    user_id: UUID
    stage: int
    choices: list[UUID]
    ended: bool
    is_refreshed: bool


class RatingSchema(NewRatingSchema):
    id: UUID


class RatingPaginatedResponseSchema(PaginatedResponse):
    data: list[RatingSchema]


class RatingChoiceResponseSchema(BaseModel):
    id: UUID
    items: list[UUID]
    stage: int = 1
    round: int
    prev: UUID | None = None
    next: UUID | None = None
    winner_id: UUID | None = None


class ChoosePayloadSchema(BaseModel):
    winner_id: UUID


class ChooseResponseSchema(BaseModel):
    next_choice: RatingChoiceResponseSchema | None = None
    ended: bool
