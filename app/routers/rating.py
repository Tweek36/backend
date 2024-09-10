from uuid import UUID
from fastapi import APIRouter, Depends
from app.routers import MaxPerPageType, PageType
from app.schemas.rating import (
    ChoosePayloadSchema,
    RatingResponseSchema,
    RatingPaginatedResponseSchema,
    StartRatingPayloadSchema,
    StartRatingResponseSchema,
)
from app.services.rating import RatingService
from app.utils.token import httpbearer


router = APIRouter(prefix="/rating", tags=["Rating"])


@router.get("/", response_model=list[RatingResponseSchema])
async def get_list(
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_list()


@router.get("/paginated/", response_model=RatingPaginatedResponseSchema)
async def get_paginated_list(
    max_per_page: MaxPerPageType,
    page: PageType,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get_paginated_list(max_per_page=max_per_page, page=page)


@router.get("/{id}/", response_model=RatingResponseSchema)
async def get(
    id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.get(id=id)


@router.post(
    "/start/{competition_id}/",
    response_model=StartRatingResponseSchema,
    dependencies=[Depends(httpbearer)],
)
async def start(
    competition_id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.start(competition_id=competition_id)


@router.post("/{id}/refresh/{choice_id}/", dependencies=[Depends(httpbearer)])
async def refresh(
    id: UUID,
    choice_id: UUID,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.refresh(id=id, choice_id=choice_id)


@router.post("/{id}/choose/{choice_id}/", dependencies=[Depends(httpbearer)])
async def choose(
    id: UUID,
    choice_id: UUID,
    payload: ChoosePayloadSchema,
    service: RatingService = Depends(RatingService.get_service),
):
    return await service.choose(id=id, choice_id=choice_id, payload=payload)
