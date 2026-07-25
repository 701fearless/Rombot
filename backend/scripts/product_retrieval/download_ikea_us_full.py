"""
Download the full IKEA US catalog (~30k products) from Hugging Face and
normalize into data/product_index/catalog.jsonl + images/.

Dataset: jeffreyszhou/ikea-us-products-2025
  - products-us.jsonl (~50MB)
  - images-us/* hero images (~5–8GB)

Usage:
  # 10% per category (recommended)
  python scripts/product_retrieval/download_ikea_us_full.py --sample-ratio 0.1 --workers 20

  # full catalog (long; several GB)
  python scripts/product_retrieval/download_ikea_us_full.py --workers 20

  # small smoke test
  python scripts/product_retrieval/download_ikea_us_full.py --limit 200

Optional mirror (China):
  $env:HF_ENDPOINT='https://hf-mirror.com'
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    CATALOG_PATH,
    DATA_ROOT,
    HF_US_DATASET,
    HF_US_IMAGES_PREFIX,
    HF_US_JSONL,
    IMAGES_DIR,
    ensure_dirs,
    save_meta,
)


FURNITURE_KEYWORDS = (
    "sofa",
    "armchair",
    "chair",
    "table",
    "desk",
    "bed",
    "mattress",
    "wardrobe",
    "cabinet",
    "shelf",
    "bookcase",
    "storage",
    "tv",
    "sideboard",
    "dresser",
    "chest",
    "nightstand",
    "bench",
    "stool",
    "ottoman",
    "furniture",
    "couch",
    "loveseat",
    "sectional",
    "dining",
    "coffee table",
    "side table",
    "rug",
    "carpet",
    "lamp",
    "lighting",
    "mirror",
    "curtain",
)


def _hf_base() -> str:
    endpoint = (os.getenv("HF_ENDPOINT") or "https://huggingface.co").rstrip("/")
    # hf-mirror.com serves the same /datasets/.../resolve/ paths
    return endpoint


def _resolve_url(relative_path: str) -> str:
    # HF requires URL-encoded path segments for spaces / unicode
    encoded = "/".join(quote(part, safe="") for part in relative_path.split("/"))
    return f"{_hf_base()}/datasets/{HF_US_DATASET}/resolve/main/{encoded}"


def _safe_stem(product_id: str, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(product_id or fallback))
    return (text[:80] or fallback)


def _is_furniture(row: dict) -> bool:
    blob = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("description") or ""),
            " ".join(str(x) for x in (row.get("category_tree") or [])),
        ]
    ).lower()
    return any(token in blob for token in FURNITURE_KEYWORDS)


def _category_key(row: dict) -> str:
    tree = [str(x) for x in (row.get("category_tree") or []) if x]
    if tree and tree[0].lower() == "products":
        tree = tree[1:]
    if not tree:
        return "unknown"
    # Prefer leaf category so sampling covers varieties; fall back to top-level.
    if len(tree) >= 2:
        return f"{tree[0]} / {tree[-1]}"
    return tree[0]


def sample_by_category(rows: list[dict], ratio: float, *, seed: int = 42) -> list[dict]:
    """Keep ~ratio of each category (at least 1 when the bucket is non-empty)."""
    ratio = max(0.0, min(1.0, float(ratio)))
    if ratio >= 0.999:
        return rows
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        buckets[_category_key(row)].append(row)

    rng = random.Random(seed)
    chosen: list[dict] = []
    for key, items in sorted(buckets.items(), key=lambda kv: kv[0]):
        rng.shuffle(items)
        if ratio <= 0 or not items:
            take = 0
        else:
            # Strict ~ratio per category. Tiny buckets: keep 1 with probability=ratio
            # (avoid "max(1)" exploding when there are thousands of 1-item categories).
            take = int(round(len(items) * ratio))
            if take < 1:
                take = 1 if rng.random() < ratio else 0
            take = min(len(items), take)
        if take:
            chosen.extend(items[:take])
        if take or len(items) >= 8:
            print(f"  sample {key}: {take}/{len(items)}", flush=True)
    rng.shuffle(chosen)
    return chosen


def download_jsonl(client: httpx.Client) -> Path:
    ensure_dirs()
    dest = DATA_ROOT / "ikea_us_products.jsonl"
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"Reuse existing JSONL: {dest} ({dest.stat().st_size} bytes)")
        return dest
    url = _resolve_url(HF_US_JSONL)
    print(f"Downloading catalog JSONL...\n  {url}")
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        tmp = dest.with_suffix(".jsonl.part")
        written = 0
        with tmp.open("wb") as out:
            for chunk in response.iter_bytes():
                out.write(chunk)
                written += len(chunk)
                if written % (5 * 1024 * 1024) < len(chunk):
                    print(f"  ... {written / 1_048_576:.1f} MB")
        tmp.replace(dest)
    print(f"Saved JSONL: {dest} ({dest.stat().st_size} bytes)")
    return dest


def _image_urls(relative_or_name: str) -> list[str]:
    name = Path(str(relative_or_name).replace("\\", "/")).name
    # HF mirror often 404s image blobs; IKEA CDN filename matches dataset local names.
    return [
        f"https://www.ikea.com/us/en/images/products/{name}",
        _resolve_url(f"{HF_US_IMAGES_PREFIX}/{name}"),
    ]


def download_image(client: httpx.Client, relative_or_name: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    last_error: Exception | None = None
    for url in _image_urls(relative_or_name):
        try:
            response = client.get(url, follow_redirects=True, timeout=60.0)
            response.raise_for_status()
            ctype = (response.headers.get("content-type") or "").lower()
            if "image" not in ctype and not url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue
            image = Image.open(BytesIO(response.content)).convert("RGB")
            dest.parent.mkdir(parents=True, exist_ok=True)
            image.save(dest, format="JPEG", quality=88)
            return True
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue
    print(f"  skip image: {Path(str(relative_or_name)).name[:60]} ({last_error})")
    return False


def row_to_record(row: dict, image_rel: str | None) -> dict:
    product_id = str(row.get("product_id") or "").strip()
    title = str(row.get("title") or "").replace(" - IKEA US", "").strip()
    tree = [str(x) for x in (row.get("category_tree") or []) if x]
    # drop leading "Products"
    if tree and tree[0].lower() == "products":
        tree = tree[1:]
    price_raw = row.get("price")
    try:
        price = float(str(price_raw).replace(",", "").replace("$", "")) if price_raw not in (None, "") else None
    except ValueError:
        price = None
    materials = row.get("materials") or []
    if isinstance(materials, list):
        material_text = "; ".join(str(x) for x in materials)
    else:
        material_text = str(materials)
    return {
        "productId": f"ikea_{product_id}" if product_id else f"ikea_{hash(title) & 0xfffffff}",
        "title": title or product_id,
        "productName": title.split(",")[0].strip() if title else product_id,
        "category1": tree[0] if len(tree) > 0 else None,
        "category2": tree[1] if len(tree) > 1 else (tree[0] if tree else None),
        "category3": tree[2] if len(tree) > 2 else None,
        "category4": tree[3] if len(tree) > 3 else None,
        "categoryTree": tree,
        "description": row.get("description"),
        "price": price,
        "currency": "USD",
        "size_m": None,
        "measurements": None,
        "materialAndCare": material_text or None,
        "features": "; ".join(str(x) for x in (row.get("good_to_know") or [])) or None,
        "productUrl": row.get("source_url"),
        "primaryImageUrl": None,
        "localImage": image_rel,
        "source": HF_US_DATASET,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download full IKEA US catalog for CLIP index")
    parser.add_argument("--limit", type=int, default=0, help="Max products after sampling (0 = all)")
    parser.add_argument("--sleep", type=float, default=0.0, help="Optional delay after each image")
    parser.add_argument("--workers", type=int, default=16, help="Parallel image download workers")
    parser.add_argument("--skip-images", action="store_true", help="Metadata only")
    parser.add_argument(
        "--furniture-only",
        action="store_true",
        help="Keep sofas/tables/beds/storage/lighting-ish rows (smaller, better for room demo)",
    )
    parser.add_argument(
        "--sample-ratio",
        type=float,
        default=1.0,
        help="Fraction to keep per category (e.g. 0.1 = 10%% of each variety)",
    )
    parser.add_argument("--sample-seed", type=int, default=42, help="RNG seed for per-category sampling")
    parser.add_argument("--force-jsonl", action="store_true", help="Re-download products-us.jsonl")
    args = parser.parse_args()

    ensure_dirs()
    if args.force_jsonl:
        old = DATA_ROOT / "ikea_us_products.jsonl"
        if old.exists():
            old.unlink()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    with httpx.Client(headers=headers, timeout=180.0) as client:
        jsonl_path = download_jsonl(client)

    candidates: list[dict] = []
    scanned = 0
    with jsonl_path.open(encoding="utf-8") as src:
        for line in src:
            line = line.strip()
            if not line:
                continue
            scanned += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if args.furniture_only and not _is_furniture(row):
                continue
            candidates.append(row)

    if args.sample_ratio < 0.999:
        print(
            f"Sampling {args.sample_ratio:.0%} per category from {len(candidates)} candidates...",
            flush=True,
        )
        candidates = sample_by_category(candidates, args.sample_ratio, seed=args.sample_seed)

    if args.limit:
        candidates = candidates[: args.limit]

    jobs: list[dict] = []
    for index, row in enumerate(candidates, start=1):
        product_id = str(row.get("product_id") or index)
        stem = _safe_stem(product_id, f"row_{index}")
        image_refs = row.get("image_urls") or []
        jobs.append(
            {
                "row": row,
                "product_id": product_id,
                "image_path": IMAGES_DIR / f"{stem}.jpg",
                "image_ref": str(image_refs[0]) if image_refs else None,
            }
        )
    print(f"Queued {len(jobs)} products (scanned={scanned})", flush=True)

    def process_job(job: dict) -> tuple[dict | None, str | None]:
        row = job["row"]
        image_path: Path = job["image_path"]
        image_ref = job["image_ref"]
        if args.skip_images:
            return row_to_record(row, None), None
        if not image_ref:
            return None, "missing image ref"
        with httpx.Client(headers=headers, timeout=60.0) as worker_client:
            ok = download_image(worker_client, image_ref, image_path)
        if args.sleep:
            time.sleep(args.sleep)
        if not ok:
            return None, "image download failed"
        image_rel = str(image_path.relative_to(DATA_ROOT)).replace("\\", "/")
        return row_to_record(row, image_rel), None

    kept = 0
    skipped = 0
    write_lock = threading.Lock()
    staging_catalog = DATA_ROOT / "catalog_us_building.jsonl"
    with staging_catalog.open("w", encoding="utf-8") as out:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(process_job, job): job for job in jobs}
            for future in as_completed(futures):
                record, error = future.result()
                if record is None:
                    skipped += 1
                else:
                    line = json.dumps(record, ensure_ascii=False) + "\n"
                    with write_lock:
                        out.write(line)
                        kept += 1
                done = kept + skipped
                if done % 100 == 0 or done == len(jobs):
                    print(
                        f"  progress: kept={kept} skipped={skipped} done={done}/{len(jobs)}",
                        flush=True,
                    )

    backup = DATA_ROOT / "catalog_home_decor_backup.jsonl"
    if CATALOG_PATH.exists() and CATALOG_PATH.stat().st_size > 0 and not backup.exists():
        CATALOG_PATH.replace(backup)
    staging_catalog.replace(CATALOG_PATH)

    save_meta(
        {
            "stage": "download",
            "dataset": HF_US_DATASET,
            "catalogPath": str(CATALOG_PATH.relative_to(ROOT)).replace("\\", "/"),
            "imagesDir": str(IMAGES_DIR.relative_to(ROOT)).replace("\\", "/"),
            "count": kept,
            "skipped": skipped,
            "scanned": scanned,
            "furnitureOnly": bool(args.furniture_only),
            "sampleRatio": args.sample_ratio,
            "sampleSeed": args.sample_seed,
            "workers": args.workers,
        }
    )
    print(f"Done. catalog={CATALOG_PATH} count={kept} skipped={skipped} scanned={scanned}")
    print("Next: rebuild CLIP index with .venv-retrieval:")
    print(
        r"  .\.venv-retrieval\Scripts\python.exe scripts\product_retrieval\build_index.py "
        r"--pretrained data\product_index\ViT-B-32.pt"
    )


if __name__ == "__main__":
    main()
