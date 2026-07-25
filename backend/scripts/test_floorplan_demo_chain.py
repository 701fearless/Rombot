from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app


FLOORPLAN_ROOT = BACKEND_ROOT / "sample_data" / "floorplans"


def assert_preprocessed_presets() -> None:
    manifest = json.loads(
        (FLOORPLAN_ROOT / "presets.json").read_text(encoding="utf-8")
    )
    presets = manifest["presets"]
    expected_scene_ids = [f"room{index}" for index in range(1, 8)]
    assert [item["sceneId"] for item in presets] == expected_scene_ids
    placeholder_glb = (FLOORPLAN_ROOT / "whitebox.glb").read_bytes()
    assert placeholder_glb[:4] == b"glTF"

    for preset in presets:
        scene_id = preset["sceneId"]
        source_path = FLOORPLAN_ROOT / f"{scene_id}.png"
        scene_path = FLOORPLAN_ROOT / "preprocessed" / scene_id / "normalized_scene.json"
        glb_path = FLOORPLAN_ROOT / "preprocessed" / scene_id / "whitebox.glb"

        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == preset["sourceSha256"]
        assert json.loads(scene_path.read_text(encoding="utf-8"))["sceneId"] == scene_id
        assert glb_path.read_bytes() == placeholder_glb


def assert_demo_apis() -> None:
    with TestClient(app) as client:
        presets_response = client.get("/api/floorplan/presets")
        assert presets_response.status_code == 200
        assert len(presets_response.json()["presets"]) == 7

        room_response = client.get("/api/floorplan/presets/room1")
        assert room_response.status_code == 200
        room = room_response.json()
        assert room["sceneId"] == "room1"
        assert room["quality"] == "placeholder"
        room_glb_response = client.get(room["whiteboxGlbUrl"])
        assert room_glb_response.status_code == 200
        assert room_glb_response.content == (FLOORPLAN_ROOT / "whitebox.glb").read_bytes()

        assert client.get("/api/floorplan/presets/not-a-room").status_code == 404

        asset_response = client.get(
            "/api/feed/prebuilt-asset",
            params={"frameId": "2_000002", "objectId": "obj_sofa_001"},
        )
        assert asset_response.status_code == 200
        asset = asset_response.json()
        assert asset["deduplicatedObjectId"] == "candidate_sofa_001"
        assert asset["glbUrl"].endswith(
            "/videos/2/generated/candidate_sofa_001/generated_model.glb"
        )
        assert asset["estimatedDimensions"]
        furniture_glb_response = client.get(asset["glbUrl"])
        assert furniture_glb_response.status_code == 200
        assert furniture_glb_response.content[:4] == b"glTF"

        # Video 3 has an analyzed object but no competition-time cached model.
        missing_response = client.get(
            "/api/feed/prebuilt-asset",
            params={"frameId": "3_000001", "objectId": "obj_armchair_001"},
        )
        assert missing_response.status_code == 404


if __name__ == "__main__":
    assert_preprocessed_presets()
    assert_demo_apis()
    print("floorplan demo chain: PASS")
