"""Shared paths and helpers for offline IKEA CLIP/FAISS retrieval."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = BACKEND_ROOT / "data" / "product_index"
IMAGES_DIR = DATA_ROOT / "images"
CATALOG_PATH = DATA_ROOT / "catalog.jsonl"
EMBEDDINGS_PATH = DATA_ROOT / "embeddings.npy"
FAISS_INDEX_PATH = DATA_ROOT / "index.faiss"
META_PATH = DATA_ROOT / "meta.json"

HF_DATASET = "crawlfeeds/IKEA-Home-Decor-Furniture-Dataset"
HF_CSV_URL = (
    "https://huggingface.co/datasets/crawlfeeds/IKEA-Home-Decor-Furniture-Dataset/"
    "resolve/main/crawlfeeds_ikea__limit-100000_category_1-home-decor_20260409_190938.csv"
)

# Full US catalog (~30k products, includes sofas/tables/beds — not just Home Decor)
HF_US_DATASET = "jeffreyszhou/ikea-us-products-2025"
HF_US_JSONL = "products-us.jsonl"
HF_US_IMAGES_PREFIX = "images-us"

# OpenCLIP defaults (demo-friendly)
DEFAULT_CLIP_MODEL = "ViT-B-32"
DEFAULT_CLIP_PRETRAINED = "openai"


def ensure_dirs() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def parse_primary_image(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"nan", "none", "null", "\\n"}:
        return None
    if text.startswith("http"):
        # Sometimes multiple URLs joined
        for part in re.split(r"[\s,|]+", text):
            if part.startswith("http"):
                return part
        return text.split()[0]
    # JSON list / dict
    if text.startswith("[") or text.startswith("{"):
        try:
            parsed = json.loads(text.replace("'", '"'))
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list) and parsed:
            first = parsed[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                return first.get("url") or first.get("src")
        if isinstance(parsed, dict):
            return parsed.get("url") or parsed.get("src") or parsed.get("primary")
    return None


def parse_measurements_m(raw: Any) -> list[float] | None:
    """Best-effort Width/Depth/Height cm → [w,h,d] meters."""
    if raw is None:
        return None
    text = str(raw)
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    def find_cm(keys: tuple[str, ...]) -> float | None:
        for key in keys:
            match = re.search(rf"{key}\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*cm", text, flags=re.I)
            if match:
                return float(match.group(1)) / 100.0
        return None

    width = find_cm(("width", "w", "直径", "diameter"))
    height = find_cm(("height", "h"))
    depth = find_cm(("depth", "d", "length", "l"))
    if width is None and height is None and depth is None:
        # bare numbers with cm
        nums = [float(x) / 100.0 for x in re.findall(r"([0-9]+(?:\.[0-9]+)?)\s*cm", text, flags=re.I)]
        if len(nums) >= 3:
            return [nums[0], nums[1], nums[2]]
        return None
    return [
        width if width is not None else 0.4,
        height if height is not None else 0.4,
        depth if depth is not None else 0.4,
    ]


def load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    items: list[dict[str, Any]] = []
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"skip bad catalog line {line_no}: {exc}")
    return items


def save_meta(payload: dict[str, Any]) -> None:
    ensure_dirs()
    META_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta() -> dict[str, Any]:
    if not META_PATH.exists():
        return {}
    return json.loads(META_PATH.read_text(encoding="utf-8"))
