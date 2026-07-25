"""Mock catalog plus product recognition and recommendation APIs."""

from fastapi import APIRouter, HTTPException

from app.schemas import (
    MockProductSearchRequest,
    ProductMatch,
    ProductRecognizeAndRecommendRequest,
    ProductRecognizeAndRecommendResponse,
    ProductRecognizeRequest,
    ProductRecognizeResponse,
    ProductRecommendRequest,
    ProductRecommendResponse,
    ProductSearchResponse,
)
from app.services.product.recognize import recognize_product
from app.services.product.recommend import recommend_products


router = APIRouter()


MOCK_PRODUCTS: dict[str, list[tuple[str, str, int, str]]] = {
    "sofa": [
        ("mock_sofa_001", "模块三人沙发", 3999, "220 × 90 × 84 cm"),
        ("mock_sofa_002", "紧凑双人沙发", 2499, "168 × 86 × 82 cm"),
        ("mock_sofa_003", "高靠背休闲沙发", 3299, "196 × 92 × 96 cm"),
    ],
    "coffee_table": [
        ("mock_table_001", "橡木纹茶几", 699, "110 × 55 × 42 cm"),
        ("mock_table_002", "双层收纳茶几", 899, "100 × 60 × 45 cm"),
        ("mock_table_003", "圆形边几组合", 599, "70 × 70 × 40 cm"),
    ],
    "chair": [
        ("mock_chair_001", "弧背餐椅", 399, "48 × 53 × 79 cm"),
        ("mock_chair_002", "软包休闲椅", 799, "68 × 72 × 82 cm"),
        ("mock_chair_003", "轻量工作椅", 599, "58 × 60 × 88 cm"),
    ],
    "bed": [
        ("mock_bed_001", "软包双人床架", 2299, "180 × 210 × 98 cm"),
        ("mock_bed_002", "带抽屉储物床", 2999, "180 × 215 × 92 cm"),
        ("mock_bed_003", "简约木质床架", 1699, "150 × 205 × 90 cm"),
    ],
    "wardrobe": [
        ("mock_storage_001", "双门衣柜", 1999, "120 × 60 × 210 cm"),
        ("mock_storage_002", "推拉门衣柜", 3299, "180 × 65 × 220 cm"),
        ("mock_storage_003", "开放式衣物柜", 1299, "100 × 55 × 200 cm"),
    ],
    "cabinet": [
        ("mock_cabinet_001", "组合收纳柜", 1299, "120 × 40 × 80 cm"),
        ("mock_cabinet_002", "窄边餐边柜", 1599, "140 × 42 × 86 cm"),
        ("mock_cabinet_003", "高脚展示柜", 1899, "90 × 38 × 180 cm"),
    ],
    "dining_table": [
        ("mock_dining_001", "六人餐桌", 1899, "160 × 85 × 75 cm"),
        ("mock_dining_002", "可伸缩餐桌", 2499, "140/200 × 85 × 75 cm"),
        ("mock_dining_003", "圆形四人餐桌", 1499, "110 × 110 × 75 cm"),
    ],
    "desk": [
        ("mock_desk_001", "双抽屉书桌", 999, "120 × 60 × 75 cm"),
        ("mock_desk_002", "升降工作桌", 2199, "140 × 70 × 72-118 cm"),
        ("mock_desk_003", "紧凑壁靠书桌", 699, "100 × 50 × 75 cm"),
    ],
}

FALLBACK_PRODUCTS = [
    ("mock_generic_001", "简约家居单品", 599, "尺寸待确认"),
    ("mock_generic_002", "多功能收纳单品", 899, "尺寸待确认"),
    ("mock_generic_003", "轻量家居单品", 399, "尺寸待确认"),
]


@router.post("/mock-search", response_model=ProductSearchResponse)
async def mock_product_search(request: MockProductSearchRequest) -> ProductSearchResponse:
    label = request.label.strip().lower()
    products = MOCK_PRODUCTS.get(label, FALLBACK_PRODUCTS)
    matches = [
        ProductMatch(
            productId=product_id,
            name=name,
            category=label or "furniture",
            score=round(0.92 - index * 0.07, 2),
            priceCny=price,
            sizeText=size_text,
            reason=(
                f"Mock 类别召回：与{request.name or label or '所选家具'}同属 {label or 'furniture'}；"
                "未运行 CLIP，也不代表真实同款。"
            ),
        )
        for index, (product_id, name, price, size_text) in enumerate(products)
    ]
    return ProductSearchResponse(
        objectId=request.objectId,
        queryLabel=label,
        matches=matches,
    )

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
