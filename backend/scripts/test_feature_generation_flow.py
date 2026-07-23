import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.main import app


def data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test feature-grounded furniture generation.")
    parser.add_argument("image", type=Path, help="Local paused-frame image path.")
    parser.add_argument("--video-id", default="feature_generation_demo")
    parser.add_argument("--time", type=float, default=12.4)
    parser.add_argument("--object-id", default=None)
    args = parser.parse_args()

    if os.getenv("MODEL3D_PROVIDER") not in {"feature_hunyuan", "feature_meshy"}:
        print('Set MODEL3D_PROVIDER="feature_hunyuan" before running this script.')
    if os.getenv("MODEL3D_PROVIDER") == "feature_hunyuan":
        if not os.getenv("ARK_API_KEY"):
            print("ARK_API_KEY is empty.")
        if not os.getenv("HUNYUAN_API_KEY"):
            print("HUNYUAN_API_KEY is empty.")
        if not os.getenv("HUNYUAN_BASE_URL"):
            print("HUNYUAN_BASE_URL is empty.")
    elif os.getenv("MODEL3D_PROVIDER") == "feature_meshy":
        if not os.getenv("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is empty.")
        if not os.getenv("MESHY_API_KEY"):
            print("MESHY_API_KEY is empty.")

    image_path = args.image.resolve()
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    client = TestClient(app)
    detect_response = client.post(
        "/api/feed/detect",
        json={"videoId": args.video_id, "time": args.time, "frameImage": data_uri(image_path)},
    )
    detect_response.raise_for_status()
    detect_payload = detect_response.json()

    selected = next(
        (item for item in detect_payload["objects"] if item["id"] == args.object_id),
        detect_payload["objects"][0],
    )

    select_response = client.post(
        "/api/feed/select-object",
        json={
            "frameId": detect_payload["frameId"],
            "objectId": selected["id"],
            "frameImage": data_uri(image_path),
        },
    )
    select_response.raise_for_status()
    payload = select_response.json()

    print("taskId:", payload["taskId"])
    print("status:", payload["status"])
    print("glbUrl:", payload["object"]["glbUrl"])
    generation = payload.get("generation") or {}
    print("briefUrl:", generation.get("briefUrl"))
    print("referenceImages:")
    for item in generation.get("referenceImages", []):
        print(f"  - {item.get('type')}: {item.get('url')}")
    print("textureReferences:")
    for item in generation.get("textureReferences", []):
        print(f"  - {item.get('type')}: {item.get('url')}")


if __name__ == "__main__":
    main()
