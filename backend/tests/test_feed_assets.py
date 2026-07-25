import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers.feed import prebuilt_model_path
from app.schemas import DetectedObject


def detected(candidate_id: str | None = "candidate_chair_001") -> DetectedObject:
    return DetectedObject(
        id="obj_chair_001",
        label="chair",
        name="Chair",
        confidence=1,
        bbox=[0, 0, 10, 10],
        tagPosition=[0.5, 0.5],
        deduplicatedObjectId=candidate_id,
    )


class PrebuiltModelPathTests(unittest.TestCase):
    def test_prefers_generated_model_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "app.routers.feed.OUTPUTS_ROOT", Path(directory)
        ):
            generated = Path(directory) / "videos/4/generated/candidate_chair_001/generated_model.glb"
            fallback = Path(directory) / "videos/4/glb/candidate_chair_001.glb"
            generated.parent.mkdir(parents=True)
            fallback.parent.mkdir(parents=True)
            generated.touch()
            fallback.touch()

            self.assertEqual(prebuilt_model_path("4_000001", detected()), generated)

    def test_uses_flat_glb_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "app.routers.feed.OUTPUTS_ROOT", Path(directory)
        ):
            fallback = Path(directory) / "videos/4/glb/candidate_chair_001.glb"
            fallback.parent.mkdir(parents=True)
            fallback.touch()

            self.assertEqual(prebuilt_model_path("4_000001", detected()), fallback)

    def test_returns_none_without_candidate_or_model(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "app.routers.feed.OUTPUTS_ROOT", Path(directory)
        ):
            self.assertIsNone(prebuilt_model_path("4_000001", detected()))
            self.assertIsNone(prebuilt_model_path("4_000001", detected(None)))

    def test_videos_one_to_six_have_cached_models(self) -> None:
        client = TestClient(app)
        outputs = Path(__file__).resolve().parents[1] / "outputs" / "videos"
        for video_id in map(str, range(1, 7)):
            analysis = json.loads((outputs / video_id / "analysis.json").read_text(encoding="utf-8"))
            response = client.post(
                "/api/feed/detect",
                json={"videoId": video_id, "time": analysis["frames"][0]["time"]},
            )
            self.assertEqual(response.status_code, 200, video_id)
            objects = response.json()["objects"]
            self.assertTrue(any(item.get("prebuiltGlbUrl") for item in objects), video_id)


if __name__ == "__main__":
    unittest.main()
