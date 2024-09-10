from uuid import UUID
from pydantic import BaseModel
from app.schemas.competition import CompetitionItemResponseSchema
from app.utils.pagination import PaginatedResponse


class RatingResponseSchema(BaseModel):
    id: UUID
    competition_id: UUID
    user_id: UUID
    stage: int
    choices: list[UUID]
    ended: bool
    is_refreshed: bool


class RatingPaginatedResponseSchema(PaginatedResponse):
    data: list[RatingResponseSchema]


class StartRatingPayloadSchema(BaseModel):
    competition_id: UUID


class RatingChoiceResponseSchema(BaseModel):
    id: UUID
    items: list[CompetitionItemResponseSchema]
    stage: int = 1


class StartRatingResponseSchema(BaseModel):
    rating_id: UUID
    cur_choice: RatingChoiceResponseSchema


class RefreshRatingPayloadSchema(BaseModel):
    from_prev: bool = False


class ChoosePayloadSchema(BaseModel):
    winner_id: UUID
    looser_id: UUID


class ChooseResponseSchema(BaseModel):
    next_choice: RatingChoiceResponseSchema | None = None
    ended: bool
