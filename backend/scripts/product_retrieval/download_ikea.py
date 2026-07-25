"""
Download IKEA Home Decor CSV from Hugging Face, fetch primary images, write local catalog.

Usage (backend venv is fine; only needs httpx/Pillow):
  python scripts/product_retrieval/download_ikea.py
  python scripts/product_retrieval/download_ikea.py --limit 100
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from io import BytesIO, StringIO
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    CATALOG_PATH,
    DATA_ROOT,
    HF_CSV_URL,
    HF_DATASET,
    IMAGES_DIR,
    ensure_dirs,
    parse_measurements_m,
    parse_primary_image,
    save_meta,
)


def _safe_stem(product_id: str, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(product_id or fallback))
    return (text[:80] or fallback)


def download_csv(client: httpx.Client) -> str:
    print(f"Downloading CSV...\n  {HF_CSV_URL}")
    response = client.get(HF_CSV_URL, follow_redirects=True)
    response.raise_for_status()
    raw_path = DATA_ROOT / "ikea_raw.csv"
    raw_path.write_bytes(response.content)
    print(f"Saved raw CSV: {raw_path} ({len(response.content)} bytes)")
    return response.text


def download_image(client: httpx.Client, url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        response = client.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, format="JPEG", quality=90)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  skip image: {url[:80]}... ({exc})")
        return False


def row_to_record(row: dict[str, str], image_rel: str | None) -> dict:
    product_id = str(row.get("product_id") or row.get("item_number") or row.get("uniq_id") or "")
    name = str(row.get("product_name") or "").strip()
    title = str(row.get("description") or name).strip()
    if name and title and name.lower() not in title.lower():
        title = f"{name} {title}"
    price_raw = row.get("price")
    try:
        price = float(str(price_raw).replace(",", "")) if price_raw not in (None, "") else None
    except ValueError:
        price = None
    size_m = parse_measurements_m(row.get("measurements"))
    return {
        "productId": f"ikea_{product_id}" if product_id else f"ikea_{hash(title) & 0xfffffff}",
        "title": title or name or product_id,
        "productName": name,
        "category1": row.get("category_1"),
        "category2": row.get("category_2"),
        "category3": row.get("category_3"),
        "category4": row.get("category_4"),
        "description": row.get("summary") or row.get("description"),
        "price": price,
        "currency": row.get("currency") or "INR",
        "size_m": size_m,
        "measurements": row.get("measurements"),
        "materialAndCare": row.get("material_and_care"),
        "features": row.get("features"),
        "productUrl": row.get("product_url"),
        "primaryImageUrl": parse_primary_image(row.get("primary_image")),
        "localImage": image_rel,
        "source": HF_DATASET,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download IKEA catalog + images for offline CLIP index")
    parser.add_argument("--limit", type=int, default=0, help="Max products (0 = all)")
    parser.add_argument("--sleep", type=float, default=0.05, help="Delay between image downloads")
    parser.add_argument("--skip-images", action="store_true", help="Only write catalog metadata")
    args = parser.parse_args()

    ensure_dirs()
    with httpx.Client(
        headers={"User-Agent": "RoombotProductRetrieval/0.1 (hackathon demo)"},
        timeout=120.0,
    ) as client:
        csv_text = download_csv(client)
        # HF dump occasionally embeds NUL bytes that break csv.DictReader
        csv_text = csv_text.replace("\x00", "")
        reader = csv.DictReader(StringIO(csv_text))
        rows = list(reader)
        print(f"CSV rows: {len(rows)}")

        kept = 0
        skipped = 0
        with CATALOG_PATH.open("w", encoding="utf-8") as out:
            for index, row in enumerate(rows):
                if args.limit and kept >= args.limit:
                    break
                image_url = parse_primary_image(row.get("primary_image"))
                product_id = str(row.get("product_id") or row.get("item_number") or index)
                stem = _safe_stem(product_id, f"row_{index}")
                image_path = IMAGES_DIR / f"{stem}.jpg"
                image_rel: str | None = None

                if args.skip_images:
                    image_rel = None
                elif not image_url:
                    skipped += 1
                    continue
                else:
                    ok = download_image(client, image_url, image_path)
                    if not ok:
                        skipped += 1
                        continue
                    image_rel = str(image_path.relative_to(DATA_ROOT)).replace("\\", "/")
                    if args.sleep:
                        time.sleep(args.sleep)

                record = row_to_record(row, image_rel)
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                kept += 1
                if kept % 25 == 0:
                    print(f"  progress: {kept} saved, {skipped} skipped")

    save_meta(
        {
            "stage": "download",
            "dataset": HF_DATASET,
            "catalogPath": str(CATALOG_PATH.relative_to(ROOT)).replace("\\", "/"),
            "imagesDir": str(IMAGES_DIR.relative_to(ROOT)).replace("\\", "/"),
            "count": kept,
            "skipped": skipped,
        }
    )
    print(f"Done. catalog={CATALOG_PATH} count={kept} skipped={skipped}")


if __name__ == "__main__":
    main()
