"""
Build OpenCLIP embeddings + FAISS (or numpy) index from local IKEA catalog images.

Prefer a Python 3.9–3.12 venv (torch/open_clip may not support 3.14 yet):

  py -3.9 -m venv .venv-retrieval
  .\\.venv-retrieval\\Scripts\\python.exe -m pip install -r requirements-product-retrieval.txt
  .\\.venv-retrieval\\Scripts\\python.exe scripts\\product_retrieval\\build_index.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    CATALOG_PATH,
    DATA_ROOT,
    DEFAULT_CLIP_MODEL,
    DEFAULT_CLIP_PRETRAINED,
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    META_PATH,
    ensure_dirs,
    load_catalog,
    load_meta,
    save_meta,
)


def _load_clip(model_name: str, pretrained: str, device: str):
    try:
        import open_clip
        import torch
    except ImportError as exc:
        raise SystemExit(
            "Missing open_clip/torch. Create .venv-retrieval with Python 3.9–3.12 and install "
            "requirements-product-retrieval.txt"
        ) from exc

    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
    model = model.to(device)
    model.eval()
    return torch, model, preprocess


def encode_images(
    image_paths: list[Path],
    *,
    model_name: str,
    pretrained: str,
    device: str,
    batch_size: int,
) -> np.ndarray:
    torch, model, preprocess = _load_clip(model_name, pretrained, device)
    vectors: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[start : start + batch_size]
            images = []
            for path in batch_paths:
                image = Image.open(path).convert("RGB")
                images.append(preprocess(image))
            tensor = torch.stack(images).to(device)
            feats = model.encode_image(tensor)
            feats = feats / feats.norm(dim=-1, keepdim=True)
            vectors.append(feats.detach().cpu().numpy().astype("float32"))
            print(f"  encoded {min(start + batch_size, len(image_paths))}/{len(image_paths)}")
    return np.concatenate(vectors, axis=0)


def build_faiss(embeddings: np.ndarray) -> None:
    try:
        import faiss
    except ImportError:
        print("faiss not installed — skipping index.faiss (search will use numpy cosine)")
        if FAISS_INDEX_PATH.exists():
            FAISS_INDEX_PATH.unlink()
        return
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    # serialize via Python IO — faiss C++ FileIOWriter breaks on non-ASCII Windows paths
    FAISS_INDEX_PATH.write_bytes(faiss.serialize_index(index).tobytes())
    print(f"Wrote FAISS index: {FAISS_INDEX_PATH} (ntotal={index.ntotal})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build OpenCLIP + FAISS product index")
    parser.add_argument("--model", default=DEFAULT_CLIP_MODEL)
    parser.add_argument("--pretrained", default=DEFAULT_CLIP_PRETRAINED)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    ensure_dirs()
    if not CATALOG_PATH.exists():
        raise SystemExit(f"Catalog missing. Run download_ikea.py first: {CATALOG_PATH}")

    catalog = load_catalog()
    usable = []
    image_paths: list[Path] = []
    for item in catalog:
        rel = item.get("localImage")
        if not rel:
            continue
        path = DATA_ROOT / rel
        if not path.exists():
            continue
        usable.append(item)
        image_paths.append(path)

    if not usable:
        raise SystemExit("No local images found in catalog. Re-run download_ikea.py without --skip-images")

    print(f"Encoding {len(usable)} images with OpenCLIP {args.model}/{args.pretrained} on {args.device}")
    embeddings = encode_images(
        image_paths,
        model_name=args.model,
        pretrained=args.pretrained,
        device=args.device,
        batch_size=args.batch_size,
    )
    np.save(EMBEDDINGS_PATH, embeddings)
    print(f"Wrote embeddings: {EMBEDDINGS_PATH} shape={embeddings.shape}")

    # Rewrite catalog in the same order as embeddings (only indexed rows)
    indexed_catalog = DATA_ROOT / "catalog_indexed.jsonl"
    with indexed_catalog.open("w", encoding="utf-8") as fh:
        for item in usable:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    build_faiss(embeddings)

    meta = load_meta()
    meta.update(
        {
            "stage": "index",
            "clipModel": args.model,
            "clipPretrained": args.pretrained,
            "device": args.device,
            "indexedCount": len(usable),
            "embeddingDim": int(embeddings.shape[1]),
            "embeddingsPath": str(EMBEDDINGS_PATH.relative_to(ROOT)).replace("\\", "/"),
            "faissPath": str(FAISS_INDEX_PATH.relative_to(ROOT)).replace("\\", "/")
            if FAISS_INDEX_PATH.exists()
            else None,
            "catalogIndexedPath": str(indexed_catalog.relative_to(ROOT)).replace("\\", "/"),
        }
    )
    save_meta(meta)
    print(f"Meta: {META_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
