import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import scene_snapshot


class SceneSnapshotApiTest(unittest.TestCase):
    def setUp(self) -> None:
        test_root = scene_snapshot.BACKEND_ROOT / "outputs"
        test_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=test_root)
        self.output_patch = patch.object(scene_snapshot, "OUTPUTS_ROOT", Path(self.temporary.name))
        self.output_patch.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.output_patch.stop()
        self.temporary.cleanup()

    def test_room6_snapshot_round_trip(self) -> None:
        initial_response = self.client.get("/api/room/snapshots/room6")
        self.assertEqual(initial_response.status_code, 200)
        initial = initial_response.json()
        self.assertEqual(initial["sceneId"], "room6")
        self.assertEqual(initial["revision"], 0)
        self.assertEqual(initial["coordinateSystem"], "threejs-xz-ground-y-up")

        changed = deepcopy(initial)
        changed["objects"][0]["transform"]["position"][0] = 2.25
        saved_response = self.client.put("/api/room/snapshots/room6", json=changed)
        self.assertEqual(saved_response.status_code, 200)
        saved = saved_response.json()
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["objects"][0]["transform"]["position"][0], 2.25)
        self.assertEqual(self.client.get("/api/room/snapshots/room6").json(), saved)

        reset = self.client.post("/api/room/snapshots/room6/reset").json()
        self.assertEqual(reset["revision"], 0)
        self.assertNotEqual(reset["objects"][0]["transform"]["position"][0], 2.25)

    def test_snapshot_validation(self) -> None:
        snapshot = self.client.get("/api/room/snapshots/room6").json()
        mismatch = deepcopy(snapshot)
        mismatch["sceneId"] = "room1"
        self.assertEqual(self.client.put("/api/room/snapshots/room6", json=mismatch).status_code, 400)

        invalid = deepcopy(snapshot)
        invalid["objects"][0]["geometry"]["size"][0] = 0
        self.assertEqual(self.client.put("/api/room/snapshots/room6", json=invalid).status_code, 422)
        self.assertEqual(self.client.get("/api/room/snapshots/room8").status_code, 404)
        with self.assertRaises(ValueError):
            scene_snapshot.runtime_path("../room6")


if __name__ == "__main__":
    unittest.main()
