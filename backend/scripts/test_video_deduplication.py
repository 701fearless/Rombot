import sys
import shutil
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas import DetectedObject, VideoAnalysisFrame
from app.services.video_preprocess.clip_deduplicator import ClipFurnitureDeduplicator
from app.storage.local_store import OUTPUTS_ROOT, path_to_output_url


class FakeEncoder:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self.embeddings = embeddings

    def encode(self, image_paths: list[Path], batch_size: int) -> list[list[float]]:
        return self.embeddings[: len(image_paths)]


class FailingEncoder:
    def encode(self, image_paths: list[Path], batch_size: int) -> list[list[float]]:
        raise RuntimeError("test encoder failure")


class VideoDeduplicationTest(unittest.TestCase):
    @contextmanager
    def _test_directory(self):
        root = OUTPUTS_ROOT / f"_dedupe_test_{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            yield root
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def _make_frames(self, root: Path, labels: list[str]) -> list[VideoAnalysisFrame]:
        frames: list[VideoAnalysisFrame] = []
        for index, label in enumerate(labels, start=1):
            frame_path = root / "frames" / f"{index:06d}.jpg"
            crop_path = root / "objects" / f"crop_{index:06d}.jpg"
            frame_path.parent.mkdir(parents=True, exist_ok=True)
            crop_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (200, 160), (220, 220, 220)).save(frame_path)
            Image.new("RGB", (100, 100), (100 + index, 80, 60)).save(crop_path)
            frames.append(
                VideoAnalysisFrame(
                    frameId=f"video_{index:06d}",
                    time=float(index - 1),
                    frameImageUrl=path_to_output_url(frame_path),
                    objects=[
                        DetectedObject(
                            id=f"obj_{label}_{index:03d}",
                            label=label,
                            name=label,
                            confidence=0.8 + index * 0.01,
                            bbox=[20, 20, 120, 120],
                            tagPosition=[0.35, 0.44],
                            cropUrl=path_to_output_url(crop_path),
                        )
                    ],
                )
            )
        return frames

    def _deduplicator(self, encoder) -> ClipFurnitureDeduplicator:
        return ClipFurnitureDeduplicator(
            threshold=0.88,
            batch_size=16,
            model_name="unused-in-tests",
            device="cpu",
            encoder=encoder,
        )

    def test_similar_objects_in_one_video_are_merged(self) -> None:
        with self._test_directory() as root:
            frames = self._make_frames(root, ["chair", "chair"])
            candidates, warning = self._deduplicator(FakeEncoder([[1.0, 0.0], [0.99, 0.1]])).deduplicate(
                "video_a", frames, root
            )

            self.assertIsNone(warning)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].duplicateCount, 2)
            self.assertTrue((root / "deduplicated" / candidates[0].id / "annotated.jpg").exists())

    def test_different_visuals_or_labels_are_not_merged(self) -> None:
        with self._test_directory() as root:
            frames = self._make_frames(root, ["chair", "chair", "table"])
            candidates, _ = self._deduplicator(
                FakeEncoder([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]])
            ).deduplicate("video_a", frames, root)

            self.assertEqual(len(candidates), 3)

    def test_group_state_does_not_cross_video_calls(self) -> None:
        with self._test_directory() as root:
            first_root = root / "video_a"
            second_root = root / "video_b"
            first = self._make_frames(first_root, ["chair", "chair"])
            second = self._make_frames(second_root, ["chair"])
            deduplicator = self._deduplicator(FakeEncoder([[1.0, 0.0], [1.0, 0.0]]))

            first_candidates, _ = deduplicator.deduplicate("video_a", first, first_root)
            second_candidates, _ = deduplicator.deduplicate("video_b", second, second_root)

            self.assertEqual(first_candidates[0].duplicateCount, 2)
            self.assertEqual(second_candidates[0].duplicateCount, 1)

    def test_encoder_failure_keeps_every_detection(self) -> None:
        with self._test_directory() as root:
            frames = self._make_frames(root, ["chair", "chair"])
            candidates, warning = self._deduplicator(FailingEncoder()).deduplicate("video_a", frames, root)

            self.assertEqual(len(candidates), 2)
            self.assertTrue(all(candidate.duplicateCount == 1 for candidate in candidates))
            self.assertIn("test encoder failure", warning or "")


if __name__ == "__main__":
    unittest.main()
