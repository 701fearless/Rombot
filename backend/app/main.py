from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import debug, feed, floorplan, health, room, video


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
app.include_router(debug.router, prefix="/api/debug", tags=["debug"])
app.include_router(floorplan.router, prefix="/api/floorplan", tags=["floorplan"])

app.mount("/sample_data", StaticFiles(directory="sample_data"), name="sample_data")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/static", StaticFiles(directory="static"), name="static")


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_ROOT = FRONTEND_DIST.resolve()

if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        requested_path = (FRONTEND_DIST / full_path).resolve()
        if requested_path.is_file() and (
            requested_path == FRONTEND_ROOT or FRONTEND_ROOT in requested_path.parents
        ):
            return FileResponse(requested_path)

        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend build not found")
