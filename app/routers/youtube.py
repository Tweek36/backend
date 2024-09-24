from fastapi import APIRouter, Depends, Query
from app.schemas.competition_item import CompetitionItemSchema
from app.schemas.youtube import AddPlaylistPayloadSchema, GetVideoTitleResponseSchema
from app.services.youtube import YouTubeService
from app.utils.token import AccessToken, get_access_token_data


router = APIRouter(prefix="/youtube", tags=["YouTube"])


@router.get("/video-title/", response_model=GetVideoTitleResponseSchema)
async def get_video_title(
    id: str = Query(pattern=r"^[a-zA-Z0-9_-]{11}$"),
    authorization: AccessToken = Depends(get_access_token_data),
    service: YouTubeService = Depends(YouTubeService.get_service),
):
    return await service.get_video_title(id=id)


@router.post("/add/playlist/", response_model=list[CompetitionItemSchema])
async def add_playlis_videos(
    payload: AddPlaylistPayloadSchema,
    authorization: AccessToken = Depends(get_access_token_data),
    service: YouTubeService = Depends(YouTubeService.get_service),
):
    return await service.add_playlis_videos(payload=payload, user_id=authorization.sub)
