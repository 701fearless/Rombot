"""
Match ALL images under ../vedios against the local CLIP product index.

Writes:
  - outputs/shop/vedios_library_matches.json  (full library + topK products)
  - outputs/shop/products/<id>.json          (white-label product snapshots)
  - outputs/videos/<videoId>/product_matches.json  (deduplicated crops subset, API compat)

  .\\.venv-retrieval\\Scripts\\python.exe scripts\\product_retrieval\\batch_match_vedios_all.py ^
    --top-k 5 --pretrained data\\product_index\\ViT-B-32.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DEFAULT_CLIP_MODEL, EMBEDDINGS_PATH, load_meta  # noqa: E402
from search import (  # noqa: E402
    encode_with_model,
    hit_to_product,
    load_clip_model,
    load_indexed_catalog,
    search,
)

from app.services.shop_store import (  # noqa: E402
    IMAGE_SUFFIXES,
    VEDIOS_ROOT,
    save_library_matches,
    to_shop_product,
    upsert_products,
)


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def collect_images() -> list[Path]:
    if not VEDIOS_ROOT.is_dir():
        raise FileNotFoundError(f"Missing vedios root: {VEDIOS_ROOT}")
    return sorted(
        path
        for path in VEDIOS_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def main() -> None:
    _configure_stdout()
    parser = argparse.ArgumentParser(description="Batch CLIP-match all vedios images")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model", default=None)
    parser.add_argument("--pretrained", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap for smoke tests")
    args = parser.parse_args()

    meta = load_meta()
    model_name = args.model or meta.get("model") or DEFAULT_CLIP_MODEL
    pretrained = args.pretrained or meta.get("pretrained") or "openai"

    images = collect_images()
    if args.limit and args.limit > 0:
        images = images[: args.limit]
    print(f"vedios images: {len(images)}")
    print(f"index: {EMBEDDINGS_PATH}")

    catalog = load_indexed_catalog()
    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")
    model, preprocess, _tokenizer = load_clip_model(
        model_name=model_name, pretrained=pretrained, device=args.device
    )

    items: list[dict] = []
    per_video: dict[str, dict] = {}

    for index, path in enumerate(images, start=1):
        rel = path.relative_to(VEDIOS_ROOT).as_posix()
        parts = rel.split("/")
        video_id = parts[0] if parts else "unknown"
        kind = parts[1] if len(parts) > 1 else ""
        print(f"[{index}/{len(images)}] {rel}")

        query = encode_with_model(path, model, preprocess, args.device)
        scores, indices = search(query, embeddings, args.top_k)
        products_raw = []
        for rank, (score, idx) in enumerate(zip(scores.tolist(), indices.tolist()), start=1):
            if idx < 0 or idx >= len(catalog):
                continue
            products_raw.append(hit_to_product(catalog[idx], rank, float(score)))
        products = [
            to_shop_product(row, rank=row.get("rank"), score=row.get("score"))
            for row in products_raw
        ]
        upsert_products(products)

        entry = {
            "id": rel.replace("/", "__"),
            "videoId": video_id,
            "kind": kind,
            "relativePath": rel,
            "imageUrl": f"/vedios/{rel}",
            "products": products,
        }
        items.append(entry)

        # Keep API-compatible cache for deduplicated crops
        if kind == "deduplicated" and path.name.lower() == "crop.jpg":
            candidate_id = parts[2] if len(parts) > 2 else path.parent.name
            bucket = per_video.setdefault(video_id, {})
            bucket[candidate_id] = {
                "label": candidate_id.split("_")[1] if "_" in candidate_id else candidate_id,
                "name": candidate_id,
                "cropUrl": f"/vedios/{rel}",
                "products": products,
            }

    payload = {
        "savedAt": datetime.now(timezone.utc).isoformat(),
        "videosRoot": str(VEDIOS_ROOT.resolve()),
        "imageCount": len(items),
        "topK": args.top_k,
        "model": model_name,
        "pretrained": pretrained,
        "items": items,
    }
    out = save_library_matches(payload)
    print(f"library matches -> {out}")

    for video_id, matches in per_video.items():
        out_dir = ROOT / "outputs" / "videos" / video_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "product_matches.json"
        path.write_text(
            json.dumps(
                {
                    "videoId": video_id,
                    "savedAt": datetime.now(timezone.utc).isoformat(),
                    "topK": args.top_k,
                    "provider": "local_clip",
                    "matches": matches,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"video cache -> {path} ({len(matches)} crops)")

    print("done")


if __name__ == "__main__":
    main()
