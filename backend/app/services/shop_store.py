"""Local shop catalog helpers: white-label products + persistent search results."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_ROOT = BACKEND_ROOT / "outputs"
SHOP_ROOT = OUTPUTS_ROOT / "shop"
SEARCH_LOG_PATH = SHOP_ROOT / "search_results.jsonl"
LIBRARY_MATCHES_PATH = SHOP_ROOT / "vedios_library_matches.json"
PRODUCTS_DIR = SHOP_ROOT / "products"
CATALOG_INDEXED = BACKEND_ROOT / "data" / "product_index" / "catalog_indexed.jsonl"
CATALOG_PATH = BACKEND_ROOT / "data" / "product_index" / "catalog.jsonl"
VEDIOS_ROOT = BACKEND_ROOT.parent / "vedios"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

_catalog_by_id: dict[str, dict[str, Any]] | None = None


def ensure_shop_dirs() -> None:
    SHOP_ROOT.mkdir(parents=True, exist_ok=True)
    PRODUCTS_DIR.mkdir(parents=True, exist_ok=True)


def public_product_id(raw_id: str | None) -> str:
    text = str(raw_id or "").strip()
    if text.lower().startswith("ikea_"):
        return text[5:]
    return text or "unknown"


def _strip_brand_text(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"(?i)\bikea\b", "", str(text))
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -|/:")
    return cleaned


def _as_feature_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = str(value).strip()
        if not text:
            return []
        items = [part.strip() for part in re.split(r"[;\n]+", text) if part.strip()]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        item = _strip_brand_text(item)
        key = item.lower()
        if not item or key in seen:
            continue
        seen.add(key)
        cleaned.append(item)
    return cleaned


def _format_size_m(size_m: Any) -> str | None:
    if not size_m:
        return None
    if isinstance(size_m, (list, tuple)) and len(size_m) >= 2:
        labels = ("宽", "高", "深")
        parts = []
        for index, value in enumerate(size_m[:3]):
            try:
                parts.append(f"{labels[index]} {float(value):.2f} m")
            except (TypeError, ValueError):
                continue
        return " × ".join(parts) if parts else None
    if isinstance(size_m, dict):
        mapping = [
            ("width", "宽"),
            ("height", "高"),
            ("depth", "深"),
            ("w", "宽"),
            ("h", "高"),
            ("d", "深"),
        ]
        parts = []
        for key, label in mapping:
            if key in size_m and size_m[key] is not None:
                try:
                    parts.append(f"{label} {float(size_m[key]):.2f} m")
                except (TypeError, ValueError):
                    continue
        return " × ".join(parts) if parts else None
    return _strip_brand_text(str(size_m)) or None


def to_shop_product(
    item: dict[str, Any],
    *,
    rank: int | None = None,
    score: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert an index/catalog row into a white-label shop product (no outbound URL)."""
    raw_id = item.get("productId")
    product_id = public_product_id(raw_id)
    local_image = item.get("localImage")
    image_url = item.get("imageUrl")
    if local_image and not (image_url or "").startswith("/"):
        image_url = f"/product_index/{local_image}"
    elif not image_url and local_image:
        image_url = f"/product_index/{local_image}"

    title = _strip_brand_text(item.get("productName") or item.get("title"))
    description = _strip_brand_text(item.get("description"))
    category = _strip_brand_text(item.get("category2") or item.get("category1"))
    subcategory = _strip_brand_text(item.get("category3") or item.get("category4"))
    category_tree = [
        _strip_brand_text(part)
        for part in (item.get("categoryTree") or [])
        if _strip_brand_text(part)
    ]
    if not category_tree:
        category_tree = [
            part
            for part in [
                _strip_brand_text(item.get("category1")),
                category,
                subcategory,
                _strip_brand_text(item.get("category4")),
            ]
            if part
        ]

    features = _as_feature_list(item.get("features"))
    material = _strip_brand_text(item.get("materialAndCare"))
    measurements_raw = item.get("measurements")
    measurements_text = None
    if isinstance(measurements_raw, dict):
        measurements_text = "；".join(
            f"{_strip_brand_text(k)}: {_strip_brand_text(v)}"
            for k, v in measurements_raw.items()
            if _strip_brand_text(str(v))
        ) or None
    elif measurements_raw:
        measurements_text = _strip_brand_text(str(measurements_raw)) or None
    size_text = _format_size_m(item.get("size_m"))

    row: dict[str, Any] = {
        "productId": product_id,
        "sku": product_id,
        "title": title or product_id,
        "productName": title or product_id,
        "description": description,
        "features": features,
        "materialAndCare": material,
        "measurements": measurements_raw,
        "measurementsText": measurements_text,
        "size_m": item.get("size_m"),
        "sizeText": size_text,
        "price": item.get("price"),
        "currency": item.get("currency") or "USD",
        "category": category,
        "subcategory": subcategory,
        "category1": _strip_brand_text(item.get("category1")),
        "category2": category,
        "category3": subcategory,
        "category4": _strip_brand_text(item.get("category4")),
        "categoryTree": category_tree,
        "localImage": local_image,
        "imageUrl": image_url,
        "detailUrl": f"/static/shop.html#/p/{product_id}",
    }
    if rank is not None:
        row["rank"] = rank
    if score is not None:
        row["score"] = round(float(score), 4)
    if item.get("rawScore") is not None:
        row["rawScore"] = item.get("rawScore")
    if item.get("labelBoost") is not None:
        row["labelBoost"] = item.get("labelBoost")
    if extra:
        row.update(extra)
    return row


def whitened_results(results: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in results or []:
        out.append(
            to_shop_product(
                item,
                rank=item.get("rank"),
                score=item.get("score"),
                extra={
                    k: item[k]
                    for k in ("rawScore", "labelBoost")
                    if k in item
                },
            )
        )
    return out


def load_catalog_by_id() -> dict[str, dict[str, Any]]:
    global _catalog_by_id
    if _catalog_by_id is not None:
        return _catalog_by_id
    path = CATALOG_INDEXED if CATALOG_INDEXED.exists() else CATALOG_PATH
    mapping: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                raw = str(row.get("productId") or "")
                if not raw:
                    continue
                mapping[raw] = row
                mapping[public_product_id(raw)] = row
    _catalog_by_id = mapping
    return mapping


def get_shop_product(product_id: str) -> dict[str, Any] | None:
    ensure_shop_dirs()
    catalog = load_catalog_by_id()
    pid = public_product_id(product_id)
    row = catalog.get(product_id) or catalog.get(pid) or catalog.get(f"ikea_{pid}")

    cached_path = PRODUCTS_DIR / f"{pid}.json"
    cached: dict[str, Any] | None = None
    if cached_path.exists():
        try:
            cached = json.loads(cached_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            cached = None

    if row is None and cached is None:
        return None

    # Prefer full catalog fields; keep ranking metadata from cache if present.
    base = dict(row or {})
    if cached:
        for key in ("rank", "score", "rawScore", "labelBoost", "imageUrl", "localImage"):
            if cached.get(key) is not None and key not in base:
                base[key] = cached[key]
            elif key in ("rank", "score", "rawScore", "labelBoost") and cached.get(key) is not None:
                base[key] = cached[key]
        if not base.get("productId"):
            base["productId"] = cached.get("productId") or pid
    product = to_shop_product(base, rank=base.get("rank"), score=base.get("score"))
    cached_path.write_text(json.dumps(product, ensure_ascii=False, indent=2), encoding="utf-8")
    return product


def upsert_products(products: list[dict[str, Any]]) -> None:
    ensure_shop_dirs()
    catalog = load_catalog_by_id()
    for item in products:
        pid = public_product_id(item.get("productId"))
        raw = catalog.get(pid) or catalog.get(f"ikea_{pid}") or item
        product = to_shop_product(raw, rank=item.get("rank"), score=item.get("score"))
        (PRODUCTS_DIR / f"{pid}.json").write_text(
            json.dumps(product, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def append_search_result(record: dict[str, Any]) -> Path:
    ensure_shop_dirs()
    payload = {
        "savedAt": datetime.now(timezone.utc).isoformat(),
        **record,
    }
    with SEARCH_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    products = payload.get("results") or payload.get("products") or []
    if isinstance(products, list):
        upsert_products(products)
    return SEARCH_LOG_PATH


def list_search_results(limit: int = 50) -> list[dict[str, Any]]:
    if not SEARCH_LOG_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    with SEARCH_LOG_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(rows[-limit:]))


def save_library_matches(payload: dict[str, Any]) -> Path:
    ensure_shop_dirs()
    LIBRARY_MATCHES_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for entry in payload.get("items") or []:
        upsert_products(entry.get("products") or [])
    return LIBRARY_MATCHES_PATH


def load_library_matches() -> dict[str, Any] | None:
    if not LIBRARY_MATCHES_PATH.exists():
        return None
    try:
        return json.loads(LIBRARY_MATCHES_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def iter_vedios_images() -> list[dict[str, Any]]:
    if not VEDIOS_ROOT.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(VEDIOS_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        rel = path.relative_to(VEDIOS_ROOT).as_posix()
        parts = rel.split("/")
        video_id = parts[0] if parts else ""
        kind = parts[1] if len(parts) > 1 else ""
        items.append(
            {
                "id": rel.replace("/", "__"),
                "videoId": video_id,
                "kind": kind,
                "relativePath": rel,
                "imageUrl": f"/vedios/{rel}",
                "absPath": str(path.resolve()),
            }
        )
    return items


def resolve_media_path(url: str) -> Path | None:
    """Resolve /outputs/, /vedios/, /product_index/ URLs to local files."""
    text = (url or "").strip()
    if not text:
        return None
    if text.startswith("/outputs/"):
        return OUTPUTS_ROOT / Path(text[len("/outputs/") :])
    if text.startswith("/vedios/"):
        return VEDIOS_ROOT / Path(text[len("/vedios/") :])
    if text.startswith("/product_index/"):
        return BACKEND_ROOT / "data" / "product_index" / Path(text[len("/product_index/") :])
    # relative vedios path
    candidate = VEDIOS_ROOT / text
    if candidate.exists():
        return candidate
    return None
