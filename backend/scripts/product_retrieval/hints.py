"""Build CLIP text queries and category rerank signals from analysis JSON."""

from __future__ import annotations

import re
from typing import Any


LABEL_POSITIVE: dict[str, tuple[str, ...]] = {
    "sofa": ("sofa", "couch", "settee", "loveseat", "armchair", "seat"),
    "armchair": ("armchair", "chair", "sofa", "seat"),
    "chair": ("chair", "stool", "seat"),
    "coffee_table": ("table", "coffee table", "side table"),
    "dining_table": ("table", "dining"),
    "table": ("table",),
    "bed": ("bed", "mattress"),
    "nightstand": ("nightstand", "bedside", "cabinet", "chest"),
    "wardrobe": ("wardrobe", "closet", "cabinet"),
    "cabinet": ("cabinet", "sideboard", "chest", "storage"),
    "bookshelf": ("shelf", "bookcase", "ledge", "storage"),
    "rug": ("rug", "carpet", "mat", "textile"),
    "curtain": ("curtain", "drape", "textile"),
    "mirror": ("mirror",),
    "painting": ("frame", "picture", "poster", "art", "wall"),
    "vase": ("vase", "bowl", "pot"),
    "plant": ("plant", "pot", "vase"),
    "chandelier": ("chandelier", "pendant", "lantern", "lamp", "light", "candle"),
    "pendant_light": ("pendant", "lantern", "lamp", "light"),
    "floor_lamp": ("lamp", "floor lamp", "light"),
    "table_lamp": ("lamp", "table lamp", "light", "lantern"),
    "tv_stand": ("tv", "media", "cabinet", "bench", "shelf"),
    "desk": ("desk", "table", "workspace"),
}

LABEL_NEGATIVE: dict[str, tuple[str, ...]] = {
    "sofa": ("tape", "hook", "adhesive", "mirror", "frame", "candle", "lantern", "ledge", "picture", "poster", "vase", "bowl"),
    "armchair": ("tape", "hook", "adhesive", "mirror", "frame", "ledge", "picture", "poster"),
    "chair": ("tape", "hook", "mirror", "frame", "candle", "ledge", "picture"),
    "coffee_table": ("tape", "hook", "mirror", "frame", "candle", "lantern", "ledge", "picture"),
    "dining_table": ("tape", "hook", "mirror", "candle", "ledge", "picture"),
    "bed": ("tape", "hook", "mirror", "candle", "lantern", "ledge"),
    "rug": ("mirror", "lantern", "candle", "tape", "hook", "vase", "frame", "ledge"),
    "curtain": ("mirror", "lantern", "candle", "tape", "vase", "frame"),
    "cabinet": ("tape", "hook", "candle", "lantern", "frame", "picture"),
    "wardrobe": ("tape", "hook", "candle", "lantern", "mirror", "frame"),
    "bookshelf": ("tape", "candle", "lantern", "mirror"),
    "chandelier": ("tape", "hook", "sofa", "rug", "mirror", "frame", "ledge"),
    "pendant_light": ("tape", "hook", "sofa", "rug", "mirror", "frame"),
    "floor_lamp": ("tape", "hook", "sofa", "rug", "mirror", "frame"),
    "table_lamp": ("tape", "hook", "sofa", "rug", "mirror", "frame"),
    "mirror": ("tape", "sofa", "rug", "candle", "ledge"),
    "vase": ("tape", "sofa", "rug", "mirror", "frame", "ledge"),
    "painting": ("tape", "sofa", "candle", "lantern", "mirror"),
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def build_query_text(hint: dict[str, Any] | None) -> str:
    if not hint:
        return ""
    parts: list[str] = []
    label = str(hint.get("label") or "").replace("_", " ").strip()
    name = str(hint.get("name") or "").strip()
    features = hint.get("visualFeatures") or {}
    if not isinstance(features, dict):
        features = {}

    # English-first: OpenCLIP ViT-B-32/openai is much stronger on English
    if label:
        colors = " ".join(_as_list(features.get("colors")))
        materials = " ".join(_as_list(features.get("materials")))
        style = str(features.get("style") or "")
        parts.append(f"a photo of a {label}")
        if colors or materials or style:
            parts.append(f"{colors} {materials} {style} {label}".strip())
        for token in LABEL_POSITIVE.get(label, ())[:4]:
            parts.append(token)

    if name:
        parts.append(name)
    if label and label.lower() not in {name.lower(), name}:
        parts.append(label)
    for key in ("style", "geometry", "texturePattern"):
        value = features.get(key)
        if value:
            parts.append(str(value))
    parts.extend(_as_list(features.get("colors")))
    parts.extend(_as_list(features.get("materials")))

    # de-dupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        key = part.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(part.strip())
    return ", ".join(ordered)[:500]


def category_adjustment(label: str | None, item: dict[str, Any]) -> float:
    if not label:
        return 0.0
    blob = " ".join(
        str(item.get(key) or "")
        for key in ("title", "category2", "category3", "productName", "description")
    ).lower()
    adj = 0.0
    for token in LABEL_POSITIVE.get(label, ()):
        if token in blob:
            adj += 0.05
    for token in LABEL_NEGATIVE.get(label, ()):
        if token in blob:
            adj -= 0.12
    return max(-0.35, min(0.22, adj))


def _match_token(haystack: str, token: str) -> bool:
    return bool(token) and token.lower() in haystack.lower()


def find_object_hint(analysis: dict[str, Any], image_ref: str) -> dict[str, Any] | None:
    """Resolve furniture hint from analysis.json using image path/name."""
    if not analysis or not image_ref:
        return None
    ref = image_ref.replace("\\", "/")
    name = ref.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]

    # candidate_sofa_001 from folder or filename
    candidate_match = re.search(r"(candidate_[a-z0-9_]+)", ref, flags=re.I)
    object_match = re.search(r"(obj_[a-z0-9_]+)", ref, flags=re.I)
    candidate_id = candidate_match.group(1) if candidate_match else None
    object_id = object_match.group(1) if object_match else None

    dedup = analysis.get("deduplicatedObjects") or []
    if candidate_id:
        for item in dedup:
            if str(item.get("id")) == candidate_id:
                return _hint_from_dedup_or_frame(analysis, item)

    frames = analysis.get("frames") or []
    if object_id:
        for frame in frames:
            for obj in frame.get("objects") or []:
                if str(obj.get("id")) == object_id:
                    return _hint_from_object(obj)

    # fuzzy: crop url / annotated path contains stem
    for item in dedup:
        urls = " ".join(
            str(item.get(key) or "")
            for key in ("cropUrl", "annotatedImageUrl", "id", "name", "label")
        )
        if _match_token(urls, stem) or _match_token(urls, name):
            return _hint_from_dedup_or_frame(analysis, item)

    for frame in frames:
        for obj in frame.get("objects") or []:
            urls = " ".join(
                str(obj.get(key) or "")
                for key in ("cropUrl", "deduplicatedCropUrl", "id", "name", "label")
            )
            if _match_token(urls, stem) or _match_token(urls, name):
                return _hint_from_object(obj)

    return None


def _hint_from_object(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": obj.get("id"),
        "deduplicatedObjectId": obj.get("deduplicatedObjectId"),
        "label": obj.get("label"),
        "name": obj.get("name"),
        "visualFeatures": obj.get("visualFeatures") or {},
        "confidence": obj.get("confidence"),
    }


def _hint_from_dedup_or_frame(analysis: dict[str, Any], dedup_item: dict[str, Any]) -> dict[str, Any]:
    candidate_id = dedup_item.get("id")
    # Prefer richest visualFeatures from any frame object linked to this candidate
    for frame in analysis.get("frames") or []:
        for obj in frame.get("objects") or []:
            if obj.get("deduplicatedObjectId") == candidate_id and obj.get("visualFeatures"):
                hint = _hint_from_object(obj)
                hint["id"] = candidate_id
                return hint
    return {
        "id": candidate_id,
        "deduplicatedObjectId": candidate_id,
        "label": dedup_item.get("label"),
        "name": dedup_item.get("name"),
        "visualFeatures": dedup_item.get("visualFeatures") or {},
        "confidence": dedup_item.get("confidence"),
    }
