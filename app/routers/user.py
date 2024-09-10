from fastapi import APIRouter, Depends
from app.routers import MaxPerPageType, PageType
from app.services.user import UserService
from app.schemas.user import PaginatedUserResponseSchema, UserResponseSchema
from app.utils.token import (
    AccessToken,
    get_access_token_data,
)
from app.schemas.competition import CompetitionPaginatedResponseSchema

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me/", response_model=UserResponseSchema)
async def me(
    authorization: AccessToken = Depends(get_access_token_data),
    service: UserService = Depends(UserService.get_service),
):
    return await service.me(authorization)


@router.get("/", response_model=PaginatedUserResponseSchema)
async def get_list(
    max_per_page: MaxPerPageType,
    page: PageType,
    service: UserService = Depends(UserService.get_service),
):
    return await service.get_paginated_list(max_per_page, page)


@router.get("/competition/", response_model=CompetitionPaginatedResponseSchema)
async def get_competitions(
    max_per_page: MaxPerPageType,
    page: PageType,
    published: bool | None = None,
    authorization: AccessToken = Depends(get_access_token_data),
    service: UserService = Depends(UserService.get_service),
):
    return await service.get_competitions(
        user_id=authorization.sub,
        published=published,
        max_per_page=max_per_page,
        page=page,
    )
