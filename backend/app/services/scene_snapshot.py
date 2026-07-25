import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import SceneSnapshot
from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT


SUPPORTED_SCENES = {"room6"}
TEMPLATE_ROOT = BACKEND_ROOT / "sample_data" / "floorplans" / "preprocessed"
MAX_WHITEBOX_BYTES = 50 * 1024 * 1024


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


def runtime_whitebox_path(scene_id: str) -> Path:
    safe_id = _validate_scene_id(scene_id)
    return OUTPUTS_ROOT / "scenes" / safe_id / "whitebox.glb"


def load_snapshot(scene_id: str) -> SceneSnapshot:
    runtime = runtime_path(scene_id)
    source = runtime if runtime.exists() else template_path(scene_id)
    if not source.exists():
        raise FileNotFoundError(f"Snapshot template not found: {scene_id}")
    snapshot = SceneSnapshot.model_validate(json.loads(source.read_text(encoding="utf-8")))
    if not snapshot.room.whiteboxGlbUrl:
        snapshot.room.whiteboxGlbUrl = (
            f"/sample_data/floorplans/preprocessed/{scene_id}/whitebox.glb"
        )
    return snapshot


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


def _validate_walls(snapshot: SceneSnapshot) -> None:
    if not snapshot.room.walls:
        raise ValueError("Snapshot must contain wall data")
    wall_ids: set[str] = set()
    for wall in snapshot.room.walls:
        start = wall.get("start")
        end = wall.get("end")
        wall_id = wall.get("id")
        if not isinstance(wall_id, str) or not wall_id or wall_id in wall_ids:
            raise ValueError("Every wall must have a unique non-empty id")
        wall_ids.add(wall_id)
        if not isinstance(start, list) or not isinstance(end, list):
            raise ValueError("Every wall must contain id, start and end")
        if len(start) != 2 or len(end) != 2:
            raise ValueError("Wall start and end must be [x, z]")
        coordinates = [*start, *end]
        if any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in coordinates):
            raise ValueError("Wall coordinates must be finite numbers")
        if math.dist(start, end) <= 0.01:
            raise ValueError("Wall length must be greater than 1 cm")
        height = wall.get("height")
        if not isinstance(height, (int, float)) or not math.isfinite(height) or height <= 0:
            raise ValueError("Wall height must be a positive finite number")


def save_runtime_whitebox(scene_id: str, snapshot: SceneSnapshot, payload: bytes) -> SceneSnapshot:
    safe_id = _validate_scene_id(scene_id)
    if snapshot.sceneId != safe_id:
        raise ValueError("Snapshot sceneId must match the URL scene id")
    if len(payload) < 12 or payload[:4] != b"glTF":
        raise ValueError("Uploaded file is not a binary glTF (GLB)")
    if len(payload) > MAX_WHITEBOX_BYTES:
        raise ValueError("Whitebox GLB exceeds the 50 MB limit")
    _validate_walls(snapshot)

    target = runtime_whitebox_path(safe_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".glb.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, target)

    updated = snapshot.model_copy(deep=True)
    updated.room.whiteboxGlbUrl = f"/outputs/scenes/{safe_id}/whitebox.glb"
    return save_snapshot(safe_id, updated)


def reset_snapshot(scene_id: str) -> SceneSnapshot:
    target = runtime_path(scene_id)
    if target.exists():
        target.unlink()
    whitebox = runtime_whitebox_path(scene_id)
    if whitebox.exists():
        whitebox.unlink()
    return load_snapshot(scene_id)
