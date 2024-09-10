from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import db_manager, redis_manager
from app.config import settings
from app.routers.user import router as user_router
from app.routers.auth import router as auth_router
from app.routers.youtube import router as youtube_router
from app.routers.rating import router as rating_router
from app.routers.competition import router as competition_router
from app.utils.token import prohibited_tokens_manager
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_manager.init(settings.DATABASE_URL)
    await redis_manager.init(settings.REDIS_URL)
    await prohibited_tokens_manager.init()
    yield
    await db_manager.close()
    await redis_manager.close()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(youtube_router)
app.include_router(rating_router)
app.include_router(competition_router)


if not os.path.exists(settings.IMAGES_FOLDER):
    os.makedirs(settings.IMAGES_FOLDER)

app.mount("/image", StaticFiles(directory=settings.IMAGES_FOLDER), name="image")
