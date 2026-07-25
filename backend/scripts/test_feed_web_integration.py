import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.services.video_preprocess.analysis_store import read_analysis


class FeedWebIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_all_feed_videos_have_cached_pause_detection(self) -> None:
        for video_id in ("2", "3", "4", "6", "7"):
            with self.subTest(video_id=video_id):
                analysis = read_analysis(video_id)
                self.assertIsNotNone(analysis)
                self.assertTrue(analysis.frames)
                frame = analysis.frames[0]
                self.assertRegex(frame.perceptualHash or "", r"^[0-9a-f]{16}$")

                response = self.client.post(
                    "/api/feed/detect",
                    json={
                        "videoId": video_id,
                        "time": frame.time,
                        "frameHash": frame.perceptualHash,
                    },
                )

                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload["frameId"], frame.frameId)
                self.assertGreater(len(payload["objects"]), 0)

    def test_built_spa_and_space_fallback_are_served(self) -> None:
        root = self.client.get("/")
        dashboard = self.client.get("/dashboard")
        space = self.client.get(
            "/space?videoId=2&time=12.40&sceneType=living_room"
            "&frameId=2_000003&objectId=obj_sofa_001&objectLabel=sofa"
        )

        self.assertEqual(root.status_code, 200)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(space.status_code, 200)
        self.assertIn("Rombot 家装灵感", root.text)
        self.assertIn('<div id="root"></div>', dashboard.text)
        self.assertIn('<div id="root"></div>', space.text)


if __name__ == "__main__":
    unittest.main()
