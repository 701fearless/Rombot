import shutil
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.schemas import VideoAnalysis, VideoAnalysisFrame
from app.services.video_preprocess.analysis_store import nearest_frame
from app.services.video_preprocess.frame_similarity import difference_hash_path
from app.storage.local_store import OUTPUTS_ROOT, file_to_data_url


class PauseFrameMatchingTest(unittest.TestCase):
    @contextmanager
    def _test_directory(self):
        root = OUTPUTS_ROOT / f"_pause_match_test_{uuid.uuid4().hex}"
        root.mkdir(parents=True, exist_ok=False)
        try:
            yield root
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def _pattern(self, path: Path, reverse: bool = False) -> None:
        image = Image.new("L", (90, 80))
        for y in range(80):
            for x in range(90):
                value = 255 - int(x * 255 / 89) if reverse else int(x * 255 / 89)
                image.putpixel((x, y), value)
        image.convert("RGB").save(path)

    def test_pause_image_selects_more_similar_following_frame(self) -> None:
        with self._test_directory() as root:
            previous_path = root / "previous.jpg"
            following_path = root / "following.jpg"
            self._pattern(previous_path)
            self._pattern(following_path, reverse=True)
            analysis = VideoAnalysis(
                videoId="video",
                status="succeeded",
                sampleIntervalSec=10,
                frames=[
                    VideoAnalysisFrame(
                        frameId="previous",
                        time=10,
                        frameImageUrl="/outputs/previous.jpg",
                        objects=[],
                        perceptualHash=difference_hash_path(previous_path),
                    ),
                    VideoAnalysisFrame(
                        frameId="following",
                        time=20,
                        frameImageUrl="/outputs/following.jpg",
                        objects=[],
                        perceptualHash=difference_hash_path(following_path),
                    ),
                ],
            )

            with patch("app.services.video_preprocess.analysis_store.read_analysis", return_value=analysis):
                selected = nearest_frame("video", 14, file_to_data_url(following_path))

            self.assertIsNotNone(selected)
            self.assertEqual(selected.frameId, "following")

    def test_pause_hash_selects_more_similar_following_frame_without_image_upload(self) -> None:
        with self._test_directory() as root:
            previous_path = root / "previous.jpg"
            following_path = root / "following.jpg"
            self._pattern(previous_path)
            self._pattern(following_path, reverse=True)
            following_hash = difference_hash_path(following_path)
            analysis = VideoAnalysis(
                videoId="video",
                status="succeeded",
                sampleIntervalSec=10,
                frames=[
                    VideoAnalysisFrame(
                        frameId="previous",
                        time=10,
                        frameImageUrl="/outputs/previous.jpg",
                        objects=[],
                        perceptualHash=difference_hash_path(previous_path),
                    ),
                    VideoAnalysisFrame(
                        frameId="following",
                        time=20,
                        frameImageUrl="/outputs/following.jpg",
                        objects=[],
                        perceptualHash=following_hash,
                    ),
                ],
            )

            with patch("app.services.video_preprocess.analysis_store.read_analysis", return_value=analysis):
                selected = nearest_frame("video", 14, pause_frame_hash=following_hash)

            self.assertIsNotNone(selected)
            self.assertEqual(selected.frameId, "following")

    def test_invalid_hash_falls_back_to_nearest_time(self) -> None:
        analysis = VideoAnalysis(
            videoId="video",
            status="succeeded",
            sampleIntervalSec=10,
            frames=[
                VideoAnalysisFrame(frameId="previous", time=10, frameImageUrl="/outputs/previous.jpg", objects=[]),
                VideoAnalysisFrame(frameId="following", time=20, frameImageUrl="/outputs/following.jpg", objects=[]),
            ],
        )
        with patch("app.services.video_preprocess.analysis_store.read_analysis", return_value=analysis):
            selected = nearest_frame("video", 12, pause_frame_hash="not-a-hash")

        self.assertIsNotNone(selected)
        self.assertEqual(selected.frameId, "previous")

    def test_equal_similarity_and_time_prefers_previous_frame(self) -> None:
        with self._test_directory() as root:
            image_path = root / "same.jpg"
            self._pattern(image_path)
            frame_hash = difference_hash_path(image_path)
            analysis = VideoAnalysis(
                videoId="video",
                status="succeeded",
                sampleIntervalSec=10,
                frames=[
                    VideoAnalysisFrame(
                        frameId="previous",
                        time=10,
                        frameImageUrl="/outputs/previous.jpg",
                        objects=[],
                        perceptualHash=frame_hash,
                    ),
                    VideoAnalysisFrame(
                        frameId="following",
                        time=20,
                        frameImageUrl="/outputs/following.jpg",
                        objects=[],
                        perceptualHash=frame_hash,
                    ),
                ],
            )

            with patch("app.services.video_preprocess.analysis_store.read_analysis", return_value=analysis):
                selected = nearest_frame("video", 15, file_to_data_url(image_path))

            self.assertIsNotNone(selected)
            self.assertEqual(selected.frameId, "previous")

    def test_video_boundary_returns_only_available_frame(self) -> None:
        analysis = VideoAnalysis(
            videoId="video",
            status="succeeded",
            sampleIntervalSec=10,
            frames=[VideoAnalysisFrame(frameId="only", time=10, frameImageUrl="/outputs/only.jpg", objects=[])],
        )
        with patch("app.services.video_preprocess.analysis_store.read_analysis", return_value=analysis):
            before = nearest_frame("video", 1, "invalid-image")
            after = nearest_frame("video", 30, "invalid-image")

        self.assertEqual(before.frameId, "only")
        self.assertEqual(after.frameId, "only")


if __name__ == "__main__":
    unittest.main()
