from __future__ import annotations

import base64
import json
import sys
import uuid
from pathlib import Path

import httpx
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.main import app
from app.routers import floorplan
from app.services.floorplan_whitebox.ai_parser import FloorplanAiParseResult
from app.services.floorplan_whitebox.schemas import FloorplanWhiteboxScene


SAMPLE_SCENE_PATH = BACKEND_ROOT / "sample_data" / "floorplans" / "sample_whitebox_scene.json"
SAMPLE_IMAGE_PATH = BACKEND_ROOT / "sample_data" / "floorplans" / "ai_test_floorplan.jpg"


class MockFloorplanParser:
    def __init__(self, **_: object) -> None:
        pass

    async def parse(self, _: str) -> FloorplanAiParseResult:
        scene = FloorplanWhiteboxScene.model_validate_json(
            SAMPLE_SCENE_PATH.read_text(encoding="utf-8-sig")
        )
        parsed = scene.model_dump()
        return FloorplanAiParseResult(
            scene=scene,
            raw_text=json.dumps(parsed, ensure_ascii=False),
            parsed_json=parsed,
            warnings=["mock parser"],
        )


class TimeoutFloorplanParser(MockFloorplanParser):
    async def parse(self, _: str) -> FloorplanAiParseResult:
        raise httpx.ReadTimeout("mock timeout")


def data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def test_build_whitebox(client: TestClient) -> None:
    payload = json.loads(SAMPLE_SCENE_PATH.read_text(encoding="utf-8-sig"))
    payload["sceneId"] = f"floorplan_api_{uuid.uuid4().hex[:8]}"
    response = client.post("/api/floorplan/build-whitebox", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    glb_path = BACKEND_ROOT / result["whiteboxGlbUrl"].lstrip("/")
    assert glb_path.read_bytes()[:4] == b"glTF"

    invalid = json.loads(json.dumps(payload))
    invalid["sceneId"] = f"floorplan_invalid_{uuid.uuid4().hex[:8]}"
    invalid["wallFixtures"][0]["wallId"] = "wall_missing"
    response = client.post("/api/floorplan/build-whitebox", json=invalid)
    assert response.status_code == 422, response.text


def test_reconstruct_with_mock(client: TestClient) -> None:
    original_parser = floorplan.ArkFloorplanParser
    floorplan.ArkFloorplanParser = MockFloorplanParser
    try:
        scene_id = f"floorplan_mock_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/floorplan/reconstruct",
            json={
                "image": data_url(SAMPLE_IMAGE_PATH),
                "sceneId": scene_id,
                "knownLength": {
                    "pixelStart": [0, 0],
                    "pixelEnd": [100, 0],
                    "meters": 2.5,
                },
            },
        )
    finally:
        floorplan.ArkFloorplanParser = original_parser

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["sceneId"] == scene_id
    assert floorplan.KNOWN_LENGTH_WARNING in result["warnings"]

    original_path = BACKEND_ROOT / result["originalImageUrl"].lstrip("/")
    glb_path = BACKEND_ROOT / result["whiteboxGlbUrl"].lstrip("/")
    raw_path = BACKEND_ROOT / result["aiRawUrl"].lstrip("/")
    assert original_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert glb_path.read_bytes()[:4] == b"glTF"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    assert raw["knownLength"]["meters"] == 2.5


def test_input_and_provider_errors(client: TestClient) -> None:
    response = client.post("/api/floorplan/reconstruct", json={})
    assert response.status_code == 422, response.text

    response = client.post(
        "/api/floorplan/reconstruct",
        json={"image": "data:image/jpeg;base64,not-valid-base64"},
    )
    assert response.status_code == 400, response.text

    response = client.post(
        "/api/floorplan/reconstruct",
        json={"imagePath": "C:/Windows/win.ini"},
    )
    assert response.status_code == 400, response.text

    original_parser = floorplan.ArkFloorplanParser
    floorplan.ArkFloorplanParser = TimeoutFloorplanParser
    try:
        response = client.post(
            "/api/floorplan/reconstruct",
            json={
                "image": data_url(SAMPLE_IMAGE_PATH),
                "sceneId": f"floorplan_timeout_{uuid.uuid4().hex[:8]}",
            },
        )
    finally:
        floorplan.ArkFloorplanParser = original_parser
    assert response.status_code == 504, response.text

    settings = get_settings()
    original_key = settings.ark_api_key
    settings.ark_api_key = None
    try:
        response = client.post(
            "/api/floorplan/reconstruct",
            json={"image": data_url(SAMPLE_IMAGE_PATH)},
        )
    finally:
        settings.ark_api_key = original_key
    assert response.status_code == 500, response.text


def main() -> None:
    client = TestClient(app)
    test_build_whitebox(client)
    test_reconstruct_with_mock(client)
    test_input_and_provider_errors(client)
    print("floorplan integration: 3 passed")


if __name__ == "__main__":
    main()
