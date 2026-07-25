import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import SceneSnapshot
from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT


SUPPORTED_SCENES = {"room6"}
TEMPLATE_ROOT = BACKEND_ROOT / "sample_data" / "floorplans" / "preprocessed"


def _validate_scene_id(scene_id: str) -> str:
    if scene_id not in SUPPORTED_SCENES:
        raise ValueError(f"Scene snapshot is not available: {scene_id}")
    return scene_id


def template_path(scene_id: str) -> Path:
    safe_id = _validate_scene_id(scene_id)
    return TEMPLATE_ROOT / safe_id / "demo_snapshot.json"


def runtime_path(scene_id: str) -> Path:
    safe_id = _validate_scene_id(scene_id)
    return OUTPUTS_ROOT / "scenes" / safe_id / "snapshot.json"


def load_snapshot(scene_id: str) -> SceneSnapshot:
    runtime = runtime_path(scene_id)
    source = runtime if runtime.exists() else template_path(scene_id)
    if not source.exists():
        raise FileNotFoundError(f"Snapshot template not found: {scene_id}")
    return SceneSnapshot.model_validate(json.loads(source.read_text(encoding="utf-8")))


def save_snapshot(scene_id: str, snapshot: SceneSnapshot) -> SceneSnapshot:
    safe_id = _validate_scene_id(scene_id)
    if snapshot.sceneId != safe_id:
        raise ValueError("Snapshot sceneId must match the URL scene id")

    try:
        current_revision = load_snapshot(safe_id).revision
    except FileNotFoundError:
        current_revision = 0

    saved = snapshot.model_copy(
        update={
            "sceneId": safe_id,
            "revision": current_revision + 1,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    target = runtime_path(safe_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(saved.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, target)
    return saved


def reset_snapshot(scene_id: str) -> SceneSnapshot:
    target = runtime_path(scene_id)
    if target.exists():
        target.unlink()
    return load_snapshot(scene_id)
