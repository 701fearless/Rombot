import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app


def main() -> None:
    client = TestClient(app)
    preprocess = client.post(
        "/api/video/preprocess",
        json={
            "videoId": "living_room_demo",
            "videoUrl": None,
            "sampleIntervalSec": 1.0,
            "mode": "mock",
            "maxFrames": 3,
        },
    )
    preprocess.raise_for_status()
    print("preprocess:", preprocess.json())

    detect = client.post("/api/feed/detect", json={"videoId": "living_room_demo", "time": 1.2})
    detect.raise_for_status()
    detect_payload = detect.json()
    print("detect:", detect_payload["frameId"], len(detect_payload["objects"]))

    selected_object = detect_payload["objects"][0]
    select = client.post(
        "/api/feed/select-object",
        json={"frameId": detect_payload["frameId"], "objectId": selected_object["id"]},
    )
    select.raise_for_status()
    select_payload = select.json()
    print("select:", select_payload["status"], select_payload["object"]["cropUrl"], select_payload["object"]["glbUrl"])

    nearest = client.get("/api/video/analysis/living_room_demo/nearest", params={"time": 1.2})
    nearest.raise_for_status()
    nearest_payload = nearest.json()
    print("nearest:", nearest_payload["frameId"], nearest_payload["time"])


if __name__ == "__main__":
    main()
