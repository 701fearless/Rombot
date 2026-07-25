"""Rule-based product recall and ranking over local catalog."""

from __future__ import annotations

from app.schemas import (
    PlacementCandidate,
    ProductRecognizeRequest,
    ProductRecommendItem,
    ProductRecommendRequest,
    ProductRecommendResponse,
    ProductRecognizeResponse,
    SceneResponse,
)
from app.services.product.catalog import load_catalog
from app.services.product.recognize import mock_recognize, recognize_product
from app.services.product.size_fit import evaluate_size_fit


def _tag_set(values: list[str] | None) -> set[str]:
    result: set[str] = set()
    for value in values or []:
        token = str(value).strip().lower()
        if token:
            result.add(token)
            result.add(token.replace(" ", "_"))
    return result


def _score_item(
    product: dict,
    query: ProductRecognizeResponse,
    *,
    budget: float | None,
    prefer_same: bool,
) -> tuple[float, str, str]:
    """Return (score, matchType, reason)."""
    category = str(product.get("category", "")).lower()
    product_tags = _tag_set([*(product.get("tags") or []), product.get("color"), product.get("material"), product.get("style"), category])
    query_tags = _tag_set([*query.queryTags, query.category, query.attributes.color or "", query.attributes.material or "", query.attributes.style or ""])

    score = 0.0
    reasons: list[str] = []

    if category == query.category.lower():
        score += 0.45
        reasons.append(f"同品类「{category}」")
    else:
        score += 0.05

    overlap = product_tags & query_tags
    if overlap:
        score += min(0.35, 0.08 * len(overlap))
        sample = "、".join(list(overlap)[:3])
        reasons.append(f"标签重合：{sample}")

    # Attribute soft match
    for field, weight, label in (
        ("color", 0.08, "颜色"),
        ("material", 0.08, "材质"),
        ("style", 0.06, "风格"),
    ):
        qv = getattr(query.attributes, field, None)
        pv = product.get(field)
        if qv and pv and (
            str(qv).lower() in str(pv).lower() or str(pv).lower() in str(qv).lower()
        ):
            score += weight
            reasons.append(f"{label}接近（{pv}）")

    price = float(product.get("price") or 0)
    if budget is not None:
        if price <= budget:
            score += 0.08
            reasons.append(f"价格¥{price:.0f}在预算内")
        else:
            score -= 0.12
            reasons.append(f"价格¥{price:.0f}超预算")

    # Size proximity vs estimated
    psize = product.get("size_m") or [0, 0, 0]
    qsize = query.estimatedSize_m
    if len(psize) >= 3 and len(qsize) >= 3:
        dims_ok = 0
        for a, b in zip(psize[:3], qsize[:3]):
            if abs(float(a) - float(b)) / max(float(b), 0.01) <= 0.15:
                dims_ok += 1
        if dims_ok >= 2:
            score += 0.12
            reasons.append("尺寸接近识别结果")
        elif dims_ok == 1:
            score += 0.05

    score = max(0.0, min(1.0, score))

    # matchType
    attr_hits = 0
    for field in ("color", "material", "style"):
        qv = getattr(query.attributes, field, None)
        pv = product.get(field)
        if qv and pv and (str(qv) in str(pv) or str(pv) in str(qv)):
            attr_hits += 1
    same = category == query.category.lower() and attr_hits >= 2 and score >= 0.75
    if prefer_same and not same:
        score *= 0.85
    match_type = "same" if same else "similar"

    if not reasons:
        reasons.append("综合相似度匹配")
    reason = "；".join(reasons[:3])
    return score, match_type, reason


async def ensure_query(request: ProductRecognizeRequest | ProductRecommendRequest) -> ProductRecognizeResponse:
    if isinstance(request, ProductRecommendRequest) and request.query is not None:
        return request.query
    recognize_req = ProductRecognizeRequest(
        objectId=getattr(request, "objectId", None),
        frameId=getattr(request, "frameId", None),
        cropUrl=getattr(request, "cropUrl", None),
        image=getattr(request, "image", None),
        label=getattr(request, "label", None),
        sceneId=getattr(request, "sceneId", None),
    )
    # Prefer explicit label path even without image
    if not any([recognize_req.image, recognize_req.cropUrl, recognize_req.objectId]):
        return mock_recognize(label=recognize_req.label)
    return await recognize_product(recognize_req)


def recommend_from_query(
    query: ProductRecognizeResponse,
    *,
    budget: float | None = None,
    prefer_same: bool = False,
    limit: int = 6,
    scene: SceneResponse | None = None,
    candidate: PlacementCandidate | None = None,
) -> list[ProductRecommendItem]:
    catalog = load_catalog()
    scored: list[tuple[float, dict, str, str]] = []
    for product in catalog:
        score, match_type, reason = _score_item(product, query, budget=budget, prefer_same=prefer_same)
        # Soft filter: keep same category first, allow a few cross-category if score high
        cat = str(product.get("category", "")).lower()
        if cat != query.category.lower() and score < 0.55:
            continue
        scored.append((score, product, match_type, reason))

    scored.sort(key=lambda row: (-row[0], float(row[1].get("price") or 0)))
    if prefer_same:
        scored.sort(key=lambda row: (0 if row[2] == "same" else 1, -row[0], float(row[1].get("price") or 0)))

    items: list[ProductRecommendItem] = []
    for score, product, match_type, reason in scored[:limit]:
        size_m = [float(x) for x in (product.get("size_m") or [1.0, 0.8, 0.6])[:3]]
        while len(size_m) < 3:
            size_m.append(0.5)
        size_fit = evaluate_size_fit(
            size_m,
            candidate=candidate,
            scene=scene,
            estimated_query_size=query.estimatedSize_m,
        )
        items.append(
            ProductRecommendItem(
                productId=str(product["productId"]),
                title=str(product.get("title") or product["productId"]),
                matchType=match_type,
                score=round(score, 3),
                price=float(product.get("price") or 0),
                currency=str(product.get("currency") or "CNY"),
                size_m=size_m,
                imageUrl=product.get("imageUrl"),
                glbUrl=product.get("glbUrl"),
                buyUrl=product.get("buyUrl"),
                reason=reason,
                sizeFit=size_fit,
                category=str(product.get("category") or ""),
                tags=[str(t) for t in (product.get("tags") or [])],
            )
        )
    return items


async def recommend_products(request: ProductRecommendRequest) -> ProductRecommendResponse:
    query = await ensure_query(request)
    items = recommend_from_query(
        query,
        budget=request.budget,
        prefer_same=request.preferSame,
        limit=request.limit,
        scene=request.scene,
        candidate=request.candidate,
    )
    return ProductRecommendResponse(query=query, items=items)
