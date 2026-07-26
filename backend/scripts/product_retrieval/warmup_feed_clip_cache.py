"""Pre-warm Feed 搜同款 local cache (no UI clicking needed).

Calls the running backend API for each generated/*/reference candidate:
  resolve-reference -> clip-search(persist=true)
which writes:
  outputs/shop/feed_clip_cache/<videoId>/<candidateId>.json
  static/mock-products/<productId>.jpg
  outputs/shop/products/<productId>.json

Usage (backend must be running on :8010):

  python scripts/product_retrieval/warmup_feed_clip_cache.py
  python scripts/product_retrieval/warmup_feed_clip_cache.py --videos 1,2,3
  python scripts/product_retrieval/warmup_feed_clip_cache.py --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_ROOT = Path(
    r"E:\xwechat_files\wxid_ps4rsn2rgwzt22_d445\msg\file\2026-07\backend\backend\outputs\videos"
)
REFERENCE_NAMES = (
    "reference_oblique_3quarter.png",
    "reference_oblique_3quarter.jpg",
    "reference.png",
    "reference.jpg",
    "reference.jpeg",
    "reference.webp",
)


def reference_videos_root() -> Path:
    env = (os.getenv("REFERENCE_VIDEOS_ROOT") or "").strip()
    if env:
        return Path(env)
    if DEFAULT_REFERENCE_ROOT.exists():
        return DEFAULT_REFERENCE_ROOT
    return BACKEND_ROOT / "outputs" / "videos"


def find_reference_file(folder: Path) -> Path | None:
    for name in REFERENCE_NAMES:
        path = folder / name
        if path.exists():
            return path
    for path in sorted(folder.glob("reference*")):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.is_file():
            return path
    return None


def label_from_candidate(name: str) -> str | None:
    match = re.match(r"^candidate_(.+)_(\d+)$", name.strip(), flags=re.I)
    return match.group(1).lower() if match else None


def cache_path(video_id: str, candidate_id: str) -> Path:
    safe_video = re.sub(r"[^\w.\-]+", "_", video_id)[:160] or "unknown"
    safe_candidate = re.sub(r"[^\w.\-]+", "_", candidate_id)[:160] or "unknown"
    return BACKEND_ROOT / "outputs" / "shop" / "feed_clip_cache" / safe_video / f"{safe_candidate}.json"


def request_json(method: str, url: str, body: dict | None = None, timeout: float = 180.0) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload) if payload else {}


def reachable(base_url: str) -> bool:
    for path in ("/api/shop/reference-root", "/health"):
        try:
            req = urllib.request.Request(f"{base_url}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.status < 300:
                    return True
        except Exception:  # noqa: BLE001
            continue
    return False


def iter_candidates(videos: list[str]) -> list[tuple[str, str]]:
    root = reference_videos_root()
    rows: list[tuple[str, str]] = []
    for video_id in videos:
        generated = root / video_id / "generated"
        if not generated.is_dir():
            print(f"[skip] missing generated: {generated}")
            continue
        for folder in sorted(p for p in generated.iterdir() if p.is_dir()):
            if find_reference_file(folder) is None:
                print(f"[skip] no reference in {folder}")
                continue
            rows.append((video_id, folder.name))
    return rows


def warmup_one(*, base_url: str, video_id: str, candidate_id: str, force: bool, top_k: int) -> str:
    path = cache_path(video_id, candidate_id)
    if path.exists() and not force:
        return "cached"

    resolve = request_json(
        "POST",
        f"{base_url}/api/shop/resolve-reference",
        {"parentFolder": video_id, "imageName": candidate_id},
        timeout=30,
    )
    reference_url = resolve.get("referenceUrl")
    if not reference_url:
        return "no-reference"

    label = label_from_candidate(candidate_id)
    body: dict = {
        "cropUrl": reference_url,
        "topK": top_k,
        "textOnly": False,
        "textWeight": 0.35 if label else 0.0,
        "persist": True,
        "imageName": candidate_id,
    }
    if label:
        body["hint"] = {"label": label}

    payload = request_json("POST", f"{base_url}/api/video/clip-search", body, timeout=240)
    count = len(payload.get("results") or [])
    if count <= 0:
        return "empty"
    return f"ok:{count}" if path.exists() or payload.get("cached") else f"ok-nofile:{count}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Warm Feed CLIP local cache for all generated candidates")
    parser.add_argument("--base-url", default=os.getenv("ROOMBOT_API", "http://127.0.0.1:8010"))
    parser.add_argument("--videos", default="1,2,3,4,5,6", help="Comma-separated video ids")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="Re-run even if cache exists")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if not reachable(base_url):
        print(f"[error] backend not reachable at {base_url}. Start uvicorn on 8010 first.")
        return 2

    videos = [part.strip() for part in args.videos.split(",") if part.strip()]
    rows = iter_candidates(videos)
    print(f"videosRoot={reference_videos_root()}")
    print(f"candidates={len(rows)} force={args.force}")

    stats = {"cached": 0, "ok": 0, "fail": 0, "skip": 0}
    started = time.time()
    for index, (video_id, candidate_id) in enumerate(rows, start=1):
        prefix = f"[{index}/{len(rows)}] {video_id}/{candidate_id}"
        try:
            status = warmup_one(
                base_url=base_url,
                video_id=video_id,
                candidate_id=candidate_id,
                force=args.force,
                top_k=args.top_k,
            )
            if status == "cached":
                stats["cached"] += 1
            elif status.startswith("ok"):
                stats["ok"] += 1
            else:
                stats["skip"] += 1
            print(f"{prefix} -> {status}")
        except urllib.error.HTTPError as exc:
            stats["fail"] += 1
            detail = exc.read().decode("utf-8", errors="replace")[:240]
            print(f"{prefix} -> HTTP {exc.code}: {detail}")
        except Exception as exc:  # noqa: BLE001
            stats["fail"] += 1
            print(f"{prefix} -> ERROR: {exc}")
        if args.sleep > 0:
            time.sleep(args.sleep)

    elapsed = time.time() - started
    print(
        "done "
        f"ok={stats['ok']} cached={stats['cached']} skip={stats['skip']} "
        f"fail={stats['fail']} elapsed={elapsed:.1f}s"
    )
    return 0 if stats["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
