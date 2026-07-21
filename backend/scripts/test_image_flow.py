import argparse
import base64
import mimetypes
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
    parser = argparse.ArgumentParser(description="Test paused-frame detection and selected-object 3D generation.")
    parser.add_argument("image", type=Path, help="Local paused-frame image path.")
    parser.add_argument("--video-id", default="local_photo_001")
    parser.add_argument("--time", type=float, default=12.4)
    parser.add_argument("--object-id", default=None, help="Object id from /api/feed/detect. Defaults to the first object.")
    args = parser.parse_args()

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

    print("frameId:", detect_payload["frameId"])
    print("objects:")
    for item in detect_payload["objects"]:
        print(f"  - {item['id']} | {item['name']} | confidence={item['confidence']} | bbox={item['bbox']}")

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
    select_payload = select_response.json()

    print("selected:", selected["id"], selected["name"])
    print("status:", select_payload["status"])
    print("glbUrl:", select_payload["object"]["glbUrl"])
    print("cropUrl:", select_payload["object"]["cropUrl"])
    print("maskUrl:", select_payload["object"]["maskUrl"])
    print("analysis:", select_payload["analysis"]["summary"])


if __name__ == "__main__":
    main()
