"""
Batch-match vedios/*/deduplicated/*/crop.jpg against the local IKEA CLIP index.

Writes outputs/videos/<videoId>/product_matches.json and optionally syncs crops.

  .\\.venv-retrieval\\Scripts\\python.exe scripts\\product_retrieval\\batch_match_products.py ^
    --videos-root ..\\vedios --video-ids 1,2,3,4,5 --top-k 3 ^
    --pretrained data\\product_index\\ViT-B-32.pt
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    DEFAULT_CLIP_MODEL,
    DEFAULT_CLIP_PRETRAINED,
    EMBEDDINGS_PATH,
    load_meta,
)
from search import (  # noqa: E402
    encode_with_model,
    hit_to_product,
    load_clip_model,
    load_indexed_catalog,
    search,
)


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def sync_deduplicated_crops(src_video_dir: Path, video_id: str) -> Path:
    """Copy deduplicated crops/metadata into outputs/videos/<id>/deduplicated."""
    src = src_video_dir / "deduplicated"
    dst = ROOT / "outputs" / "videos" / video_id / "deduplicated"
    if not src.is_dir():
        raise FileNotFoundError(f"Missing deduplicated dir: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    for candidate_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        out_dir = dst / candidate_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in ("crop.jpg", "annotated.jpg", "metadata.json"):
            src_file = candidate_dir / name
            if src_file.exists():
                shutil.copy2(src_file, out_dir / name)
    return dst


def match_video(
    video_id: str,
    src_video_dir: Path,
    *,
    model,
    preprocess,
    device: str,
    catalog: list[dict],
    embeddings: np.ndarray,
    top_k: int,
    sync_crops: bool,
) -> Path:
    dedup = src_video_dir / "deduplicated"
    if not dedup.is_dir():
        raise FileNotFoundError(f"No deduplicated folder: {dedup}")

    if sync_crops:
        sync_deduplicated_crops(src_video_dir, video_id)

    matches: dict[str, dict] = {}
    candidate_dirs = sorted(p for p in dedup.iterdir() if p.is_dir())
    for candidate_dir in candidate_dirs:
        crop = candidate_dir / "crop.jpg"
        if not crop.exists():
            print(f"  skip {candidate_dir.name}: no crop.jpg")
            continue
        meta_path = candidate_dir / "metadata.json"
        meta: dict = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))

        query = encode_with_model(crop, model, preprocess, device)
        scores, indices = search(query, embeddings, top_k)
        products = []
        for rank, (score, idx) in enumerate(zip(scores.tolist(), indices.tolist()), start=1):
            if idx < 0 or idx >= len(catalog):
                continue
            products.append(hit_to_product(catalog[idx], rank, float(score)))

        candidate_id = str(meta.get("id") or candidate_dir.name)
        crop_url = meta.get("cropUrl") or f"/outputs/videos/{video_id}/deduplicated/{candidate_id}/crop.jpg"
        matches[candidate_id] = {
            "label": meta.get("label")
            or (candidate_id.split("_")[1] if "_" in candidate_id else candidate_id),
            "name": meta.get("name") or meta.get("label") or candidate_id,
            "cropUrl": crop_url,
            "confidence": meta.get("confidence"),
            "products": products,
        }
        print(f"  {candidate_id}: {len(products)} hits (top={products[0]['title'][:48] if products else 'n/a'})")

    out_dir = ROOT / "outputs" / "videos" / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "product_matches.json"
    payload = {
        "videoId": video_id,
        "source": "ikea_clip",
        "topK": top_k,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "candidateCount": len(matches),
        "matches": matches,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    _configure_stdout()
    parser = argparse.ArgumentParser(description="Batch IKEA CLIP match for video deduplicated crops")
    parser.add_argument(
        "--videos-root",
        default=str(ROOT.parent / "vedios"),
        help="Root folder containing <videoId>/deduplicated (default: ../vedios)",
    )
    parser.add_argument("--video-ids", default="1,2,3,4,5", help="Comma-separated video ids")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--model", default=None)
    parser.add_argument("--pretrained", default=None)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument(
        "--no-sync-crops",
        action="store_true",
        help="Do not copy crops into outputs/videos/<id>/deduplicated",
    )
    args = parser.parse_args()

    videos_root = Path(args.videos_root)
    if not videos_root.is_absolute():
        videos_root = (ROOT / videos_root).resolve()
    if not videos_root.is_dir():
        raise SystemExit(f"videos root not found: {videos_root}")
    if not EMBEDDINGS_PATH.exists():
        raise SystemExit(f"Embeddings missing. Run build_index.py first: {EMBEDDINGS_PATH}")

    meta = load_meta()
    model_name = args.model or meta.get("clipModel") or DEFAULT_CLIP_MODEL
    pretrained = args.pretrained or meta.get("clipPretrained") or DEFAULT_CLIP_PRETRAINED
    # Prefer local weight file when meta still says "openai" but ViT-B-32.pt exists
    local_weight = ROOT / "data" / "product_index" / "ViT-B-32.pt"
    if pretrained == "openai" and local_weight.exists() and args.pretrained is None:
        pretrained = str(local_weight)

    catalog = load_indexed_catalog()
    embeddings = np.load(EMBEDDINGS_PATH)
    if len(catalog) != embeddings.shape[0]:
        raise SystemExit(
            f"Catalog/embedding size mismatch: catalog={len(catalog)} embeddings={embeddings.shape[0]}"
        )

    print(f"Loading CLIP {model_name} / {pretrained} on {args.device} ...")
    model, preprocess, _tokenizer = load_clip_model(
        model_name=model_name, pretrained=pretrained, device=args.device
    )

    video_ids = [part.strip() for part in args.video_ids.split(",") if part.strip()]
    sync_crops = not args.no_sync_crops
    written: list[Path] = []
    for video_id in video_ids:
        src = videos_root / video_id
        print(f"\n=== videoId={video_id} ({src}) ===")
        if not src.is_dir():
            print("  skip: folder missing")
            continue
        out = match_video(
            video_id,
            src,
            model=model,
            preprocess=preprocess,
            device=args.device,
            catalog=catalog,
            embeddings=embeddings,
            top_k=args.top_k,
            sync_crops=sync_crops,
        )
        written.append(out)
        print(f"  wrote {out}")

    print(f"\nDone: {len(written)} cache file(s)")


if __name__ == "__main__":
    main()
