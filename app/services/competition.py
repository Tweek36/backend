from datetime import datetime
import math
import os
from uuid import UUID
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from app.config import settings
from app.schemas.competition_item import (
    UpdateCompetitionItemPayloadSchema,
)
from app.services import BaseService, ModelRequests
from app.models.tests import Competition, CompetitionItem
from PIL import Image
from io import BytesIO
from pathlib import Path
import aiofiles
from app.services.youtube import YouTubeService


class CompetitionService(BaseService, ModelRequests[Competition]):
    model = Competition

    _youtube_service: YouTubeService = None

    @property
    def youtube_service(self):
        if self._youtube_service is None:
            self._youtube_service = YouTubeService(
                self.session, self.redis, self._token
            )
        return self._youtube_service

    async def _process_image(self, image: UploadFile, user_id: UUID) -> str:
        try:
            contents = await image.read()
            image_file = Image.open(BytesIO(contents))
            image_file.verify()
            file_extension = image.filename.split(".")[-1]
            image_name = f"{user_id}_{datetime.utcnow().timestamp()}.{file_extension}"
            file_path = os.path.join(Path(settings.IMAGES_FOLDER), image_name)

            async with aiofiles.open(file_path, "wb") as out_file:
                await out_file.write(contents)
            return image_name
        except Exception:
            raise HTTPException(
                status_code=400, detail="Uploaded file is not a valid image."
            )

    def _delete_old_image(self, image_name: str):
        if image_name != "default.png":
            file_path = os.path.join(Path(settings.IMAGES_FOLDER), image_name)
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass

    def _check_permission(self, instance: Competition, user_id: UUID):
        if instance.user_id != user_id:
            raise HTTPException(400, "Permission denied")

    async def get(self, **filters) -> Competition:
        stmt = select(self.model).filter_by(**filters)
        data = await self.session.scalar(stmt)
        if not data or (
            not data.published and (not self._token or data.user_id != self.token.sub)
        ):
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found"
            )
        return data

    async def post(
        self,
        title: str,
        description: str,
        category: str,
        image: UploadFile,
        **data,
    ):
        image_name = (
            await self._process_image(image, self.token.sub) if image else "default.png"
        )

        return await super().post(
            title=title,
            description=description,
            category=category,
            image=image_name,
            published=False,
            user_id=self.token.sub,
            **data,
        )

    async def update(  # noqa: F811
        self,
        id: UUID,
        **data,
    ):
        instance = await self.session.get(self.model, id)
        if not instance:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found"
            )

        if not data:
            raise HTTPException(status_code=400, detail="No data to update")

        self._check_permission(instance, self.token.sub)

        for k, v in data.items():
            if v is None:
                continue
            if k == "image":
                self._delete_old_image(instance.image)
                v = await self._process_image(v, instance.user_id)
            setattr(instance, k, v)

        await self.session.commit()
        await self.session.refresh(instance)

        return instance

    async def delete(self, id: UUID):  # noqa: F811
        instance = await self.session.get(self.model, id)
        if not instance:
            raise HTTPException(
                status_code=404, detail=f"{self.model.__name__} not found"
            )
        image = instance.image
        self._check_permission(instance, self.token.sub)
        await self.session.delete(instance)
        await self.session.commit()
        self._delete_old_image(image)
        return True

    async def get_items_list(self, id: UUID):
        competition = await self.session.get(Competition, id)
        if not competition.published:
            self._check_permission(competition, self.token.sub)
        stmt = select(CompetitionItem).filter(
            CompetitionItem.competition_id == competition.id
        )
        scalars = await self.session.stream_scalars(stmt)
        competition_items = await scalars.all()
        return competition_items

    async def get_item(self, id: UUID, user_id: UUID, item_id: UUID):
        competition = await self.session.get(Competition, id)
        self._check_permission(competition, user_id)
        competition_item = await self.session.get(CompetitionItem, item_id)
        if not competition_item or (competition_item.id != competition.id):
            raise HTTPException(
                400, "Competition item does not belong to the specified competition"
            )
        return competition_item

    async def patch_item(
        self,
        id: UUID,
        item_id: UUID,
        payload: UpdateCompetitionItemPayloadSchema,
    ):
        competition = await self.session.get(Competition, id)
        self._check_permission(competition, self.token.sub)
        stmt = select(CompetitionItem).filter(
            CompetitionItem.id == item_id, CompetitionItem.competition_id == id
        )
        competition_item = await self.session.scalar(stmt)
        if not competition_item:
            raise HTTPException(
                400,
                "Competition item not found or does not belong to the specified competition",
            )

        for k, v in payload.model_dump(exclude_none=True, exclude_unset=True).items():
            setattr(competition_item, k, v)

        if not competition_item.title:
            competition_item.title = await self.youtube_service.get_video_title(
                competition_item.videoId
            )

        await self.session.commit()
        await self.session.refresh(competition_item)
        return competition_item

    async def delete_item(self, id: UUID, item_id: UUID):
        competition = await self.session.get(Competition, id)
        self._check_permission(competition, self.token.sub)
        stmt = select(CompetitionItem).filter(
            CompetitionItem.id == item_id, CompetitionItem.competition_id == id
        )
        competition_item = await self.session.scalar(stmt)
        if not competition_item:
            raise HTTPException(
                400,
                "Competition item not found or does not belong to the specified competition",
            )
        await self.session.delete(competition_item)
        await self.session.commit()
        return True

    async def get_stages_total(self, id: UUID):
        competition = await self.get(id=id)

        stmt = select(func.count(CompetitionItem.id)).filter(
            CompetitionItem.competition_id == competition.id
        )
        items_total: int = await self.session.scalar(stmt)

        return math.ceil(math.log2(items_total))
