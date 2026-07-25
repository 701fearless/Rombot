"""Local mock product catalog loader."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = BACKEND_ROOT / "sample_data" / "products" / "catalog.json"


@lru_cache(maxsize=1)
def load_catalog() -> list[dict[str, Any]]:
    if not CATALOG_PATH.exists():
        return []
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("productId")]


def get_product(product_id: str) -> dict[str, Any] | None:
    for item in load_catalog():
        if item.get("productId") == product_id:
            return item
    return None


def list_by_category(category: str | None = None) -> list[dict[str, Any]]:
    items = load_catalog()
    if not category:
        return list(items)
    key = category.strip().lower()
    return [item for item in items if str(item.get("category", "")).lower() == key]
