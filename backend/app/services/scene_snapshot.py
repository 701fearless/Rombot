import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import SceneSnapshot
from app.storage.local_store import BACKEND_ROOT, OUTPUTS_ROOT


SUPPORTED_SCENES = {"room1", "room2", "room6"}
TEMPLATE_ROOT = BACKEND_ROOT / "sample_data" / "floorplans" / "preprocessed"
FLOORPLAN_ROOT = BACKEND_ROOT / "sample_data" / "floorplans"
VIDEOS_ROOT = OUTPUTS_ROOT / "videos"
MAX_WHITEBOX_BYTES = 50 * 1024 * 1024


def _validate_scene_id(scene_id: str) -> str:
    if scene_id not in SUPPORTED_SCENES:
        raise ValueError(f"Scene snapshot is not available: {scene_id}")
    return scene_id


def template_path(scene_id: str) -> Path:
    safe_id = _validate_scene_id(scene_id)
    return TEMPLATE_ROOT / safe_id / "demo_snapshot.json"


def _category_for_name(name: str) -> str:
    normalized = name.lower()
    categories = (
        (("sofa",), "sofa"), (("bed",), "bed"),
        (("table", "desk"), "table"), (("chair", "armchair"), "chair"),
        (("cabinet", "bookshelf", "wardrobe", "nightstand"), "storage"),
        (("lamp", "light"), "lighting"), (("rug", "carpet"), "rug"),
        (("curtain",), "curtain"),
        (("mirror", "painting", "plant", "decoration"), "decoration"),
    )
    return next((category for keys, category in categories if any(key in normalized for key in keys)), "furniture")


def _generated_asset(name: str, preferred_video_id: str | None = None) -> tuple[str | None, str | None, str | None]:
    """Resolve legacy export names deterministically across videos 1-6."""
    video_ids = [preferred_video_id] if preferred_video_id in set(map(str, range(1, 7))) else []
    video_ids.extend(video_id for video_id in map(str, range(1, 7)) if video_id not in video_ids)
    for video_id in video_ids:
        candidate = VIDEOS_ROOT / video_id / "generated" / name
        glb = candidate / "generated_model.glb"
        preview = candidate / "reference_oblique_3quarter.png"
        if glb.is_file():
            glb_url = f"/outputs/videos/{video_id}/generated/{name}/generated_model.glb"
            preview_url = f"/outputs/videos/{video_id}/generated/{name}/reference_oblique_3quarter.png" if preview.is_file() else None
            return video_id, glb_url, preview_url
    return None, None, None


def _export_snapshot(scene_id: str) -> SceneSnapshot:
    export_path = FLOORPLAN_ROOT / f"{scene_id}_export.json"
    glb_path = FLOORPLAN_ROOT / f"{scene_id}.glb"
    if not export_path.is_file() or not glb_path.is_file():
        raise FileNotFoundError(f"Snapshot template not found: {scene_id}")
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    room_data = payload.get("floorplan", {}).get("room", {})
    width = float(room_data["widthM"])
    depth = float(room_data["depthM"])
    objects = []
    for order, item in enumerate(payload.get("deduplicatedObjects") or []):
        name = str(item.get("name") or item.get("label") or f"furniture_{order + 1}")
        preferred_video_id = str(item.get("videoId") or (item.get("source") or {}).get("videoId") or "") or None
        video_id, glb_url, preview_url = _generated_asset(name, preferred_video_id)
        transform = item.get("transform") or {}
        size = transform.get("size") or [1.0, 0.8, 1.0]
        position = transform.get("position") or [width / 2, float(size[1]) / 2, depth / 2]
        rotation = transform.get("rotation") or [0.0, 0.0, 0.0]
        objects.append({
            "instanceId": str(item.get("id") or f"{scene_id}_{name}_{order + 1}"),
            "source": {"type": "preset", "videoId": video_id, "objectId": name},
            "semantic": {"label": str(item.get("label") or name), "name": name, "category": _category_for_name(name), "colors": [], "materials": [], "styles": [], "functions": []},
            "geometry": {"size": [float(value) for value in size], "glbUrl": glb_url, "cropUrl": preview_url},
            "transform": {"position": [float(value) for value in position], "rotation": [float(value) for value in rotation], "scale": [1.0, 1.0, 1.0]},
            "placement": {"isExisting": True, "locked": False, "zone": "whole_home", "surface": "floor"},
        })
    walls = [
        {"id": "wall_south", "start": [0.0, 0.0], "end": [width, 0.0], "height": 2.97},
        {"id": "wall_east", "start": [width, 0.0], "end": [width, depth], "height": 2.97},
        {"id": "wall_north", "start": [width, depth], "end": [0.0, depth], "height": 2.97},
        {"id": "wall_west", "start": [0.0, depth], "end": [0.0, 0.0], "height": 2.97},
    ]
    return SceneSnapshot.model_validate({
        "schemaVersion": "1.0", "snapshotId": f"{scene_id}_preset", "revision": 0,
        "sceneId": scene_id, "unit": "meter", "coordinateSystem": "threejs-xz-ground-y-up",
        "room": {"name": scene_id, "whiteboxGlbUrl": f"/sample_data/floorplans/{scene_id}.glb", "floorPolygon": [[0.0, 0.0], [width, 0.0], [width, depth], [0.0, depth]], "walls": walls, "openings": []},
        "objects": objects, "userContext": {}, "updatedAt": payload.get("generatedAt") or datetime.now(timezone.utc).isoformat(),
    })


def runtime_path(scene_id: str) -> Path:
    safe_id = _validate_scene_id(scene_id)
    return OUTPUTS_ROOT / "scenes" / safe_id / "snapshot.json"


def runtime_whitebox_path(scene_id: str) -> Path:
    safe_id = _validate_scene_id(scene_id)
    return OUTPUTS_ROOT / "scenes" / safe_id / "whitebox.glb"


def load_snapshot(scene_id: str) -> SceneSnapshot:
    runtime = runtime_path(scene_id)
    if not runtime.exists() and scene_id in {"room1", "room2"}:
        return _export_snapshot(scene_id)
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
