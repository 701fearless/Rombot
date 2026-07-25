from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Call the floorplan AI reconstruction API with a local image.")
    parser.add_argument(
        "image_path",
        nargs="?",
        default=str(PROJECT_ROOT / "户型图"),
        help="Local floorplan image path, or a directory whose smallest image will be used.",
    )
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="Backend server URL.")
    parser.add_argument("--scene-id", default="floorplan_ai_smoke", help="Scene id for output artifacts.")
    parser.add_argument("--timeout", type=float, default=0, help="Local API timeout in seconds. Use 0 for no timeout.")
    parser.add_argument("--retries", type=int, default=0, help="Retry count for 429 rate-limit responses.")
    parser.add_argument("--retry-delay", type=float, default=600, help="Seconds to wait before retrying a 429 response.")
    args = parser.parse_args()
    image_path = resolve_image_path(Path(args.image_path))

    payload = {
        "imagePath": str(image_path.resolve()),
        "sceneId": args.scene_id,
    }
    request = Request(
        f"{args.server.rstrip('/')}/api/floorplan/reconstruct",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout = None if args.timeout <= 0 else args.timeout
    print(f"image: {image_path}", file=sys.stderr)
    print(f"timeout: {'none' if timeout is None else timeout}", file=sys.stderr)
    data = call_with_retries(request, timeout=timeout, retries=args.retries, retry_delay=args.retry_delay)

    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"viewer: http://127.0.0.1:8787/app/services/floorplan_whitebox/viewer/index.html")
    print(f"glb: {args.server.rstrip('/')}{data['whiteboxGlbUrl']}")


def resolve_image_path(path: Path) -> Path:
    if path.is_dir():
        candidates = [
            item
            for item in path.iterdir()
            if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        if not candidates:
            raise FileNotFoundError(f"No image files found in directory: {path}")
        return sorted(candidates, key=lambda item: item.stat().st_size)[0]
    return path


def call_with_retries(request: Request, timeout: float | None, retries: int, retry_delay: float) -> dict:
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code != 429 or attempt >= retries:
                raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
            print(f"HTTP 429; waiting {retry_delay:g}s before retry {attempt + 1}/{retries}", file=sys.stderr)
            time.sleep(retry_delay)
    raise RuntimeError("unreachable retry state")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - keep CLI smoke test readable.
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
