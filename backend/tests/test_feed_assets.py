import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
