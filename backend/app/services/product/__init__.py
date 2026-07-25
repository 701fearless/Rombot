from __future__ import annotations

from app.schemas import ProductHints


def hints_from_label(label: str | None, name: str | None = None) -> ProductHints:
    category = (label or "furniture").strip().lower() or "furniture"
    tags = [category]
    if name:
        tags.append(name)
    return ProductHints(category=category, queryTags=tags, recommendApi="/api/product/recommend")
