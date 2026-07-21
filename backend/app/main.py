from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import feed, health, room, video


settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(feed.router, prefix="/api/feed", tags=["feed"])
app.include_router(room.router, prefix="/api/room", tags=["room"])
app.include_router(video.router, prefix="/api/video", tags=["video"])

app.mount("/sample_data", StaticFiles(directory="sample_data"), name="sample_data")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
