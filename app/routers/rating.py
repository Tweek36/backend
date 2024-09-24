from uuid import UUID
from fastapi import APIRouter, Depends
from app.routers import MaxPerPageType, PageType
from app.schemas.competition_item import CompetitionItemSchema
from app.schemas.rating import (
    ChoosePayloadSchema,
    ChooseResponseSchema,
    RatingChoiceResponseSchema,
    RatingSchema,
    RatingPaginatedResponseSchema,
)
from app.services.rating import RatingService
from app.utils.token import httpbearer


router = APIRouter(prefix="/rating", tags=["Rating"])


@router.get(
    "/",
    response_model=list[RatingSchema],
    dependencies=[Depends(httpbearer)],
)
async def get_list(
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_list()


@router.get(
    "/paginated/",
    response_model=RatingPaginatedResponseSchema,
    dependencies=[Depends(httpbearer)],
)
async def get_paginated_list(
    max_per_page: MaxPerPageType,
    page: PageType,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_paginated_list(max_per_page=max_per_page, page=page)


@router.post(
    "/start/{competition_id}/",
    response_model=str,
    dependencies=[Depends(httpbearer)],
)
async def start(
    competition_id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.start(competition_id=competition_id)


@router.get(
    "/{id}/grid/",
    response_model=list[list[tuple[UUID, UUID | None]]],
    dependencies=[Depends(httpbearer)],
)
async def get_grid(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_grid(id=id)


@router.get(
    "/{id}/items/",
    response_model=list[CompetitionItemSchema],
    dependencies=[Depends(httpbearer)],
)
async def get_stage_items(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_stage_items(id=id)


@router.get(
    "/{id}/items/ids/",
    response_model=list[UUID],
    dependencies=[Depends(httpbearer)],
)
async def get_available_items_ids(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service._get_available_items_ids(rating_id=id)


@router.get(
    "/{id}/rounds_total/",
    response_model=int,
    dependencies=[Depends(httpbearer)],
)
async def get_rounds_total(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_rounds_total(id=id)


@router.get(
    "/{id}/choice/last/",
    response_model=RatingChoiceResponseSchema,
    dependencies=[Depends(httpbearer)],
)
async def get_last_choice(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_last_choice(id=id)


@router.get(
    "/{id}/choice/{rating_choice_id}/",
    response_model=RatingChoiceResponseSchema,
    dependencies=[Depends(httpbearer)],
)
async def get_choice(
    id: UUID,
    rating_choice_id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_choice(rating_id=id, choice_id=rating_choice_id)


@router.get(
    "/{id}/",
    response_model=RatingSchema,
    dependencies=[Depends(httpbearer)],
)
async def get(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get(id=id)


@router.post(
    "/{id}/refresh/{choice_id}/",
    response_model=RatingChoiceResponseSchema,
    dependencies=[Depends(httpbearer)],
)
async def refresh(
    id: UUID,
    choice_id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.refresh(id=id, choice_id=choice_id)


@router.post(
    "/{id}/choose/{choice_id}/",
    response_model=ChooseResponseSchema,
    dependencies=[Depends(httpbearer)],
)
async def choose(
    id: UUID,
    choice_id: UUID,
    payload: ChoosePayloadSchema,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.choose(id=id, choice_id=choice_id, payload=payload)
