"""Product recognition and recommendation APIs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import (
    ProductRecognizeAndRecommendRequest,
    ProductRecognizeAndRecommendResponse,
    ProductRecognizeRequest,
    ProductRecognizeResponse,
    ProductRecommendRequest,
    ProductRecommendResponse,
)
from app.services.product.recognize import recognize_product
from app.services.product.recommend import recommend_products


router = APIRouter()


def _has_input(request: ProductRecognizeRequest | ProductRecommendRequest) -> bool:
    if isinstance(request, ProductRecommendRequest) and request.query is not None:
        return True
    return bool(request.objectId or request.cropUrl or request.image or request.label)


@router.post("/recognize", response_model=ProductRecognizeResponse)
async def recognize(request: ProductRecognizeRequest) -> ProductRecognizeResponse:
    if not _has_input(request):
        raise HTTPException(
            status_code=400,
            detail="Provide one of: objectId, cropUrl, image, or label",
        )
    return await recognize_product(request)


@router.post("/recommend", response_model=ProductRecommendResponse)
async def recommend(request: ProductRecommendRequest) -> ProductRecommendResponse:
    if not _has_input(request):
        raise HTTPException(
            status_code=400,
            detail="Provide query, or one of: objectId, cropUrl, image, or label",
        )
    return await recommend_products(request)


@router.post("/recognize-and-recommend", response_model=ProductRecognizeAndRecommendResponse)
async def recognize_and_recommend(
    request: ProductRecognizeAndRecommendRequest,
) -> ProductRecognizeAndRecommendResponse:
    if not _has_input(request):
        raise HTTPException(
            status_code=400,
            detail="Provide query, or one of: objectId, cropUrl, image, or label",
        )
    result = await recommend_products(request)
    return ProductRecognizeAndRecommendResponse(recognition=result.query, items=result.items)
