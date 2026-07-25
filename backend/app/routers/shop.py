"""Local shopping APIs backed by cached CLIP matches (no outbound brand links)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.reference_resolver import reference_videos_root, resolve_reference
from app.services.shop_store import (
    get_shop_product,
    iter_vedios_images,
    list_search_results,
    load_library_matches,
    public_product_id,
)

router = APIRouter()


class ResolveReferenceRequest(BaseModel):
    imageName: str = Field(min_length=1, max_length=255)
    parentFolder: str | None = Field(default=None, max_length=120)
    relativePath: str | None = None


@router.get("/library")
async def list_vedios_library(
    videoId: str | None = None,
    kind: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
) -> dict:
    items = iter_vedios_images()
    if videoId:
        items = [item for item in items if item["videoId"] == videoId]
    if kind:
        items = [item for item in items if item["kind"] == kind]
    return {
        "count": len(items),
        "items": [
            {
                "id": item["id"],
                "videoId": item["videoId"],
                "kind": item["kind"],
                "relativePath": item["relativePath"],
                "imageUrl": item["imageUrl"],
            }
            for item in items[:limit]
        ],
    }


@router.get("/products/{product_id}")
async def get_product(product_id: str) -> dict:
    product = get_shop_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {public_product_id(product_id)}")
    return product


@router.get("/search-history")
async def search_history(limit: int = Query(default=40, ge=1, le=200)) -> dict:
    return {"count": None, "items": list_search_results(limit)}


@router.get("/library-matches")
async def library_matches() -> dict:
    payload = load_library_matches()
    if not payload:
        raise HTTPException(
            status_code=404,
            detail="vedios_library_matches.json missing. Run batch_match_vedios_all.py first.",
        )
    return payload


@router.get("/reference-root")
async def get_reference_root() -> dict:
    root = reference_videos_root()
    return {"videosRoot": str(root), "exists": root.exists()}


@router.post("/resolve-reference")
async def resolve_reference_image(request: ResolveReferenceRequest) -> dict:
    """Map upload image name to generated/*/reference (parent folder inferred from leading digits)."""
    parent = request.parentFolder
    image_name = request.imageName
    if request.relativePath:
        parts = [p for p in request.relativePath.replace("\\", "/").split("/") if p]
        if parts:
            image_name = parts[-1]
    try:
        return resolve_reference(parent_folder=parent, image_name=image_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
