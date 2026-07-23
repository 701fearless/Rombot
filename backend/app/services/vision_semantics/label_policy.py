from app.schemas import DetectedObject


ALLOWED_LABELS: dict[str, str] = {
    "sofa": "沙发",
    "bed": "床",
    "chair": "椅子",
    "armchair": "单人椅",
    "dining_table": "餐桌",
    "coffee_table": "茶几",
    "desk": "书桌",
    "cabinet": "柜子",
    "wardrobe": "衣柜",
    "tv_stand": "电视柜",
    "bookshelf": "书架",
    "nightstand": "床头柜",
    "chandelier": "吊灯",
    "pendant_light": "吊灯",
    "floor_lamp": "落地灯",
    "table_lamp": "台灯",
    "rug": "地毯",
    "curtain": "窗帘",
    "plant": "绿植",
    "vase": "花器",
    "mirror": "镜子",
    "painting": "装饰画",
}

PROMPT_LABELS: dict[str, str] = {
    "dining_table": "dining table",
    "coffee_table": "coffee table",
    "tv_stand": "tv stand",
    "pendant_light": "pendant light",
    "floor_lamp": "floor lamp",
    "table_lamp": "table lamp",
}


def normalize_label(label: str) -> str:
    normalized = label.strip().lower().replace("-", "_").replace(" ", "_")
    return "_".join(part for part in normalized.split("_") if part)


def label_name(label: str, fallback: str | None = None) -> str:
    normalized = normalize_label(label)
    return fallback or ALLOWED_LABELS.get(normalized, normalized)


def is_allowed_label(label: str) -> bool:
    return normalize_label(label) in ALLOWED_LABELS


def to_grounding_prompt(labels: list[str]) -> str:
    prompt_terms = []
    for label in labels:
        normalized = normalize_label(label)
        if normalized not in ALLOWED_LABELS:
            continue
        prompt_terms.append(PROMPT_LABELS.get(normalized, normalized.replace("_", " ")))
    return " . ".join(dict.fromkeys(prompt_terms)) + (" ." if prompt_terms else "")


def filter_semantic_labels(items: list[dict], max_items: int = 6) -> list[dict]:
    filtered: list[dict] = []
    seen: set[str] = set()
    for item in items:
        normalized = normalize_label(str(item.get("label", "")))
        if normalized in seen or normalized not in ALLOWED_LABELS:
            continue
        filtered.append({"label": normalized, "name": str(item.get("name") or ALLOWED_LABELS[normalized])})
        seen.add(normalized)
        if len(filtered) >= max_items:
            break
    return filtered


def bbox_area_ratio(bbox: list[int], image_width: int, image_height: int) -> float:
    width = max(0, bbox[2] - bbox[0])
    height = max(0, bbox[3] - bbox[1])
    return (width * height) / max(1, image_width * image_height)


def tag_position(bbox: list[int], image_width: int, image_height: int) -> list[float]:
    return [
        round(((bbox[0] + bbox[2]) / 2) / max(1, image_width), 4),
        round(((bbox[1] + bbox[3]) / 2) / max(1, image_height), 4),
    ]


def iou(a: list[int], b: list[int]) -> float:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    area_a = max(0, a[2] - a[0]) * max(0, a[3] - a[1])
    area_b = max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    union = area_a + area_b - intersection
    return intersection / union if union else 0


def dedupe_objects(
    objects: list[DetectedObject],
    iou_threshold: float = 0.7,
    max_items: int = 6,
) -> list[DetectedObject]:
    deduped: list[DetectedObject] = []
    for item in sorted(objects, key=lambda obj: obj.confidence, reverse=True):
        if any(item.label == kept.label and iou(item.bbox, kept.bbox) >= iou_threshold for kept in deduped):
            continue
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


DOUBAO_FURNITURE_PROMPT = """
Identify the main furniture and home objects in this room image.
Only use these English labels:
sofa, bed, chair, armchair, dining_table, coffee_table, desk,
cabinet, wardrobe, tv_stand, bookshelf, nightstand,
chandelier, pendant_light, floor_lamp, table_lamp,
rug, curtain, plant, vase, mirror, painting.

Exclude tableware, food, books, loose decorations, people and pets.
Return at most 6 objects as JSON only:
{
  "objects": [
    {"label": "dining_table", "name": "餐桌"}
  ]
}
"""
