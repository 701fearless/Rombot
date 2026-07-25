import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.routers import furniture


class FurnitureApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        upload_dir = Path(self.temporary.name) / "uploaded_furniture"
        self.upload_patch = patch.object(furniture, "UPLOAD_DIR", upload_dir)
        self.manifest_patch = patch.object(furniture, "MANIFEST_PATH", upload_dir / "manifest.json")
        self.url_patch = patch.object(
            furniture,
            "path_to_output_url",
            side_effect=lambda path: f"/outputs/uploaded_furniture/{path.name}",
        )
        self.upload_patch.start()
        self.manifest_patch.start()
        self.url_patch.start()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.url_patch.stop()
        self.manifest_patch.stop()
        self.upload_patch.stop()
        self.temporary.cleanup()

    def test_upload_list_and_delete_glb(self) -> None:
        response = self.client.post(
            "/api/furniture/upload",
            files={"file": ("chair.glb", b"glTF" + b"\x00" * 16, "model/gltf-binary")},
        )
        self.assertEqual(response.status_code, 200)
        uploaded = response.json()
        self.assertEqual(uploaded["name"], "chair")

        listed = self.client.get("/api/furniture/list")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["id"] for item in listed.json()], [uploaded["id"]])

        deleted = self.client.delete(f"/api/furniture/{uploaded['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get("/api/furniture/list").json(), [])

    def test_rejects_wrong_extension_and_invalid_magic(self) -> None:
        wrong_extension = self.client.post(
            "/api/furniture/upload",
            files={"file": ("chair.gltf", b"glTF" + b"\x00" * 16, "model/gltf+json")},
        )
        self.assertEqual(wrong_extension.status_code, 400)

        invalid_magic = self.client.post(
            "/api/furniture/upload",
            files={"file": ("chair.glb", b"not-a-glb", "model/gltf-binary")},
        )
        self.assertEqual(invalid_magic.status_code, 400)


if __name__ == "__main__":
    unittest.main()
