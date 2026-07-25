"""
Offline visual search against the local IKEA FAISS/numpy index.

  conda activate ml2025
  python scripts\\product_retrieval\\search.py ^
    --image outputs\\1_000003\\obj_chandelier_001_002_crop.jpg --top-k 10
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
    DATA_ROOT,
    DEFAULT_CLIP_MODEL,
    DEFAULT_CLIP_PRETRAINED,
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    load_meta,
)
from hints import build_query_text, category_adjustment  # noqa: E402


def load_indexed_catalog() -> list[dict]:
    path = DATA_ROOT / "catalog_indexed.jsonl"
    if not path.exists():
        path = DATA_ROOT / "catalog.jsonl"
    items = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_clip_model(*, model_name: str, pretrained: str, device: str):
    try:
        import open_clip
    except ImportError as exc:
        raise SystemExit(
            "Missing open_clip/torch in Conda ml2025. Install "
            "requirements-product-retrieval.txt"
        ) from exc

    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
    model = model.to(device)
    model.eval()
    tokenizer = open_clip.get_tokenizer(model_name)
    return model, preprocess, tokenizer


def encode_with_model(image_path: Path, model, preprocess, device: str) -> np.ndarray:
    import torch

    image = preprocess(Image.open(image_path).convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        feat = model.encode_image(image)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.detach().cpu().numpy().astype("float32")


def encode_text_with_model(text: str, model, tokenizer, device: str) -> np.ndarray:
    import torch

    tokens = tokenizer([text]).to(device)
    with torch.no_grad():
        feat = model.encode_text(tokens)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat.detach().cpu().numpy().astype("float32")


def encode_query(image_path: Path, *, model_name: str, pretrained: str, device: str) -> np.ndarray:
    model, preprocess, _tokenizer = load_clip_model(
        model_name=model_name, pretrained=pretrained, device=device
    )
    return encode_with_model(image_path, model, preprocess, device)


def fuse_embeddings(image_feat: np.ndarray, text_feat: np.ndarray | None, text_weight: float) -> np.ndarray:
    if text_feat is None or text_weight <= 0:
        return image_feat.astype("float32")
    weight = float(min(0.85, max(0.0, text_weight)))
    fused = (1.0 - weight) * image_feat.reshape(-1) + weight * text_feat.reshape(-1)
    fused = fused / (np.linalg.norm(fused) + 1e-8)
    return fused.astype("float32").reshape(1, -1)


def hit_to_product(item: dict, rank: int, score: float, *, extra: dict | None = None) -> dict:
    row = {
        "rank": rank,
        "score": round(float(score), 4),
        "productId": item.get("productId"),
        "title": item.get("title"),
        "price": item.get("price"),
        "currency": item.get("currency"),
        "category2": item.get("category2"),
        "category3": item.get("category3"),
        "size_m": item.get("size_m"),
        "localImage": item.get("localImage"),
        "imageUrl": (
            f"/product_index/{item['localImage']}"
            if item.get("localImage")
            else item.get("primaryImageUrl")
        ),
        "productUrl": item.get("productUrl"),
    }
    if extra:
        row.update(extra)
    return row


def search(query: np.ndarray, embeddings: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
    if query.ndim == 1:
        query = query.reshape(1, -1)
    if FAISS_INDEX_PATH.exists():
        try:
            import faiss

            # deserialize via Python IO — faiss C++ FileIOReader breaks on non-ASCII Windows paths
            blob = np.frombuffer(FAISS_INDEX_PATH.read_bytes(), dtype="uint8")
            index = faiss.deserialize_index(blob)
            scores, indices = index.search(query.astype("float32"), top_k)
            return scores[0], indices[0]
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            print(f"FAISS load failed ({exc}); falling back to numpy cosine")
    # numpy cosine (embeddings are L2-normalized → dot product)
    scores = (embeddings @ query.reshape(-1)).astype("float32")
    indices = np.argsort(-scores)[:top_k]
    return scores[indices], indices


def search_with_hints(
    image_path: Path,
    *,
    catalog: list[dict],
    embeddings: np.ndarray,
    model,
    preprocess,
    tokenizer,
    device: str,
    top_k: int,
    query_text: str = "",
    label: str | None = None,
    text_weight: float = 0.4,
) -> list[dict]:
    image_feat = encode_with_model(image_path, model, preprocess, device)
    text_feat = None
    if query_text.strip():
        text_feat = encode_text_with_model(query_text.strip(), model, tokenizer, device)
    query = fuse_embeddings(image_feat, text_feat, text_weight if text_feat is not None else 0.0)

    pool = max(top_k * 12, 36)
    pool = min(pool, len(catalog))
    scores, indices = search(query, embeddings, pool)

    ranked: list[tuple[float, float, int]] = []
    for raw_score, idx in zip(scores.tolist(), indices.tolist()):
        if idx < 0 or idx >= len(catalog):
            continue
        adj = category_adjustment(label, catalog[idx])
        ranked.append((float(raw_score) + adj, float(raw_score), int(idx)))
    ranked.sort(key=lambda row: row[0], reverse=True)

    results = []
    for rank, (final_score, raw_score, idx) in enumerate(ranked[:top_k], start=1):
        results.append(
            hit_to_product(
                catalog[idx],
                rank,
                final_score,
                extra={"rawScore": round(raw_score, 4), "labelBoost": round(final_score - raw_score, 4)},
            )
        )
    return results


def main() -> None:
    # Windows consoles often default to GBK; product titles may contain Latin-1 letters
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    parser = argparse.ArgumentParser(description="Search local IKEA CLIP index with a crop image")
    parser.add_argument("--image", required=True, help="Query image path (crop / screenshot)")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--model", default=None)
    parser.add_argument("--pretrained", default=None)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--text", default="", help="Optional text hint fused into the query")
    parser.add_argument("--label", default=None, help="Furniture label for category rerank")
    parser.add_argument("--text-weight", type=float, default=0.4)
    parser.add_argument("--hints-json", default=None, help="Optional hint object JSON file")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.is_absolute():
        image_path = (ROOT / image_path).resolve()
    if not image_path.exists():
        raise SystemExit(f"Image not found: {image_path}")
    if not EMBEDDINGS_PATH.exists():
        raise SystemExit(f"Embeddings missing. Run build_index.py first: {EMBEDDINGS_PATH}")

    meta = load_meta()
    model_name = args.model or meta.get("clipModel") or DEFAULT_CLIP_MODEL
    pretrained = args.pretrained or meta.get("clipPretrained") or DEFAULT_CLIP_PRETRAINED

    catalog = load_indexed_catalog()
    embeddings = np.load(EMBEDDINGS_PATH)
    if len(catalog) != embeddings.shape[0]:
        raise SystemExit(
            f"Catalog/embedding size mismatch: catalog={len(catalog)} embeddings={embeddings.shape[0]}. "
            "Rebuild index."
        )

    hint = None
    if args.hints_json:
        hint = json.loads(Path(args.hints_json).read_text(encoding="utf-8-sig"))
    query_text = args.text or build_query_text(hint or {})
    label = args.label or (hint or {}).get("label")

    model, preprocess, tokenizer = load_clip_model(
        model_name=model_name, pretrained=pretrained, device=args.device
    )
    results = search_with_hints(
        image_path,
        catalog=catalog,
        embeddings=embeddings,
        model=model,
        preprocess=preprocess,
        tokenizer=tokenizer,
        device=args.device,
        top_k=args.top_k,
        query_text=query_text,
        label=label,
        text_weight=args.text_weight,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "query": str(image_path),
                    "queryText": query_text,
                    "label": label,
                    "textWeight": args.text_weight,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(f"Query: {image_path}")
    print(f"Text: {query_text or '(none)'}")
    print(f"Index size: {embeddings.shape[0]}  model={model_name}/{pretrained}")
    print("-" * 72)
    for row in results:
        price = row["price"]
        price_s = f"{row['currency']} {price}" if price is not None else "n/a"
        print(
            f"#{row['rank']:02d}  score={row['score']:.4f}  {price_s}\n"
            f"     {row['title']}\n"
            f"     {row.get('category2')} / {row.get('category3')}\n"
            f"     {row.get('productUrl')}"
        )


if __name__ == "__main__":
    main()
