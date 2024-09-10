from uuid import UUID
from pydantic import BaseModel, Field


class GetVideoTitleResponseSchema(BaseModel):
    video_id: str
    video_title: str


class AddPlaylistPayloadSchema(BaseModel):
    competition_id: UUID
    playlist_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{34}$")
