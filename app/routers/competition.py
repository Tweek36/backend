from uuid import UUID
from fastapi import APIRouter, Depends, Form, UploadFile, File
from app.routers import MaxPerPageType, PageType
from app.schemas.competition import (
    CompetitionItemResponseSchema,
    CompetitionResponseSchema,
    CompetitionPaginatedResponseSchema,
    CreateCompetitionItemPayloadSchema,
    UpdateCompetitionItemPayloadSchema,
)
from app.services.competition import CompetitionService


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


@router.get("/{id}/", response_model=CompetitionResponseSchema)
async def get(
    id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.get(id=id)


@router.post("/", response_model=CompetitionResponseSchema)
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


@router.patch("/{id}/", response_model=CompetitionResponseSchema)
async def update(
    id: UUID,
    image: UploadFile | None = File(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    category: str | None = Form(None),
    published: bool | None = Form(None),
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.update(
        id=id,
        image=image,
        title=title,
        description=description,
        category=category,
        published=published,
    )


@router.delete("/{id}/")
async def delete(
    id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.delete(id=id)


@router.get("/{id}/item/", response_model=list[CompetitionItemResponseSchema])
async def get_items_list(
    id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.get_items_list(id=id)


@router.get("/{id}/item/{item_id}/", response_model=CompetitionItemResponseSchema)
async def get_item(
    id: UUID,
    item_id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.get_item(id=id, item_id=item_id)


@router.post("/{id}/item/", response_model=CompetitionItemResponseSchema)
async def add_item(
    id: UUID,
    payload: CreateCompetitionItemPayloadSchema,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.add_item(id=id, payload=payload)


@router.patch("/{id}/item/{item_id}/", response_model=CompetitionItemResponseSchema)
async def patch_item(
    id: UUID,
    item_id: UUID,
    payload: UpdateCompetitionItemPayloadSchema,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.patch_item(id=id, item_id=item_id, payload=payload)


@router.delete("/{id}/item/{item_id}/")
async def delete_item(
    id: UUID,
    item_id: UUID,
    service: CompetitionService = Depends(CompetitionService.get_service),
):
    return await service.delete_item(id=id, item_id=item_id)
