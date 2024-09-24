from uuid import UUID
from fastapi import APIRouter, Depends, Form, UploadFile, File
from app.routers import (
    MaxPerPageType,
    PageType,
    OptionalMaxPerPageType,
    OptionalPageType,
)
from app.schemas.competition import (
    CompetitionSchema,
    CompetitionPaginatedResponseSchema,
)
from app.schemas.competition_item import (
    CompetitionItemPaginatedResponseSchema,
    CompetitionItemSchema,
    NewCompetitionItemSchema,
    UpdateCompetitionItemPayloadSchema,
)
from app.services.competition import CompetitionService
from app.services.competition_item import CompetitionItemService
from app.utils.token import httpbearer

router = APIRouter(prefix="/competition", tags=["Competition"])


@router.get("/", response_model=CompetitionPaginatedResponseSchema)
async def get_paginated_list(
    max_per_page: MaxPerPageType,
    page: PageType,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.get_paginated_list(
        max_per_page=max_per_page, page=page, published=True
    )


@router.post(
    "/",
    response_model=CompetitionSchema,
    dependencies=[Depends(httpbearer)],
)
async def post(
    image: UploadFile | None = File(None),
    title: str = Form(),
    description: str = Form(),
    category: str = Form(),
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.post(
        title=title,
        description=description,
        category=category,
        image=image,
    )


@router.get("/{competition_id}/", response_model=CompetitionSchema)
async def get(
    competition_id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.get(id=competition_id)


@router.patch(
    "/{competition_id}/",
    response_model=CompetitionSchema,
    dependencies=[Depends(httpbearer)],
)
async def update(
    competition_id: UUID,
    image: UploadFile | None = File(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    category: str | None = Form(None),
    published: bool | None = Form(None),
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.update(
        id=competition_id,
        image=image,
        title=title,
        description=description,
        category=category,
        published=published,
    )


@router.delete(
    "/{competition_id}/",
    dependencies=[Depends(httpbearer)],
)
async def delete(
    competition_id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.delete(id=competition_id)


@router.get(
    "/{competition_id}/item/",
    response_model=list[CompetitionItemSchema] | CompetitionItemPaginatedResponseSchema,
)
async def get_items_list(
    competition_id: UUID,
    max_per_page: OptionalMaxPerPageType = None,
    page: OptionalPageType = None,
    service: CompetitionItemService = Depends(CompetitionItemService.get_service),
):
    return await service.get_optional_paginated_list(
        max_per_page=max_per_page, page=page, competition_id=competition_id
    )


@router.get("/{competition_id}/item/{id}/", response_model=CompetitionItemSchema)
async def get_item(
    competition_id: UUID,
    id: UUID,
    service: CompetitionItemService = Depends(CompetitionItemService.get_service),
):
    return await service.get(id=id, competition_id=competition_id)


@router.post(
    "/{competition_id}/item/",
    response_model=CompetitionItemSchema,
    dependencies=[Depends(httpbearer)],
)
async def add_item(
    competition_id: UUID,
    payload: NewCompetitionItemSchema,
    service: CompetitionItemService = Depends(CompetitionItemService.get_service),
):
    return await service.post(competition_id=competition_id, **payload.model_dump())


@router.patch(
    "/{competition_id}/item/{item_id}/",
    response_model=CompetitionItemSchema,
    dependencies=[Depends(httpbearer)],
)
async def patch_item(
    competition_id: UUID,
    item_id: UUID,
    payload: UpdateCompetitionItemPayloadSchema,
    service: CompetitionItemService = Depends(CompetitionItemService.get_service),
):
    return await service.update(
        id=item_id,
        competition_id=competition_id,
        **payload.model_dump(exclude_none=True, exclude_unset=True),
    )


@router.delete(
    "/{competition_id}/item/{item_id}/",
    dependencies=[Depends(httpbearer)],
)
async def delete_item(
    competition_id: UUID,
    item_id: UUID,
    service: CompetitionItemService = Depends(CompetitionItemService.get_service),
):
    return await service.delete(id=item_id, competition_id=competition_id)


@router.get(
    "/{competition_id}/stages_total/",
    response_model=int,
    dependencies=[Depends(httpbearer)],
)
async def get_rounds_total(
    competition_id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.get_stages_total(id=competition_id)
