from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from uuid import UUID
from httpx import AsyncClient
from app.config import settings
from app.models.tests import CompetitionItem, Competition
from app.schemas.competition import CompetitionItemResponseSchema
from app.schemas.youtube import AddPlaylistPayloadSchema, GetVideoTitleResponseSchema
from app.services import BaseService
from fastapi import HTTPException


class YouTubeService(BaseService):
    async def get_video_title(self, id: str):
        params = dict(id=id, part="snippet", key=settings.YOUTUBE_API_KEY)

        async with AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos", params=params
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="Failed to fetch video details"
            )
        response_data: dict = response.json()
        try:
            items: list[dict] = response_data.get("items")
            snippet: dict = items[0].get("snippet")
            video_title: str = snippet.get("title")
        except Exception:
            return GetVideoTitleResponseSchema(video_id=id, video_title=None)
        return GetVideoTitleResponseSchema(video_id=id, video_title=video_title)

    async def add_playlis_videos(
        self, payload: AddPlaylistPayloadSchema, user_id: UUID
    ):
        stmt = select(Competition).filter(
            Competition.id == payload.competition_id, Competition.user_id == user_id
        )
        competition = await self.session.scalar(stmt)

        if not competition:
            raise HTTPException(status_code=404, detail="Competition not found")

        params = {
            "playlistId": payload.playlist_id,
            "part": "contentDetails,snippet",
            "key": settings.YOUTUBE_API_KEY,
            "maxResults": 50,
        }

        stmt = (
            insert(CompetitionItem)
            .on_conflict_do_nothing(index_elements=["competition_id", "videoId"])
            .returning(CompetitionItem)
        )

        added: list[CompetitionItemResponseSchema] = []

        async with AsyncClient() as client:
            while True:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/playlistItems", params=params
                )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail="Failed to fetch playlist details",
                    )

                response_data = response.json()
                items = response_data.get("items", [])

                result = (
                    await self.session.scalars(
                        stmt,
                        [
                            dict(
                                videoId=item["contentDetails"]["videoId"],
                                description="",
                                competition_id=payload.competition_id,
                                title=item["snippet"]["title"],
                            )
                            for item in items
                        ],
                    )
                ).all()

                added += [
                    CompetitionItemResponseSchema.model_validate(i, from_attributes=True) for i in result
                ]

                next_page_token = response_data.get("nextPageToken")
                if not next_page_token:
                    break

                params["pageToken"] = next_page_token

        await self.session.commit()

        return added
