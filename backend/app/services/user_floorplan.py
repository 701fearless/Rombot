from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.schemas import SceneSnapshot
from app.storage.local_store import BACKEND_ROOT


USER_DATA_ROOT = BACKEND_ROOT / "user"
FLOORPLAN_ROOT = BACKEND_ROOT / "sample_data" / "floorplans"
DEMO_USER_ID = "demo-user"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_id(value: str, label: str) -> str:
    if not _SAFE_ID.fullmatch(value):
        raise ValueError(f"Invalid {label}")
    return value


def user_floorplan_path(scene_id: str, user_id: str = DEMO_USER_ID) -> Path:
    return USER_DATA_ROOT / _safe_id(user_id, "user id") / "floorplans" / f"{_safe_id(scene_id, 'scene id')}_custom.json"


def _effective_size(item: Any) -> list[float]:
    return [round(item.geometry.size[index] * item.transform.scale[index], 6) for index in range(3)]


def _merge_object(existing: dict[str, Any], item: Any, order: int) -> dict[str, Any]:
    result = deepcopy(existing)
    size = _effective_size(item)
    result.update({
        "id": item.instanceId,
        "label": item.semantic.label,
        "name": item.semantic.name,
        "glbUrl": item.geometry.glbUrl,
        "transform": {
            "position": item.transform.position,
            "rotation": item.transform.rotation,
            "scale": item.transform.scale,
            "size": size,
        },
        "semantic": item.semantic.model_dump(mode="json"),
        "source": item.source.model_dump(mode="json", exclude_none=True),
        "placement": item.placement.model_dump(mode="json"),
        "isSelected": False,
        "order": order,
    })
    result["estimatedDimensions"] = {
        "widthM": size[0], "heightM": size[1], "depthM": size[2],
        "unit": "m", "source": "scene_snapshot", "isMeasured": False,
    }
    return result


def save_user_floorplan(
    snapshot: SceneSnapshot,
    user_id: str = DEMO_USER_ID,
    user_requirements: dict[str, Any] | None = None,
) -> Path:
    target = user_floorplan_path(snapshot.sceneId, user_id)
    base_path = FLOORPLAN_ROOT / f"{snapshot.sceneId}_export.json"
    source_path = target if target.is_file() else base_path
    payload: dict[str, Any] = {}
    if source_path.is_file():
        payload = json.loads(source_path.read_text(encoding="utf-8"))

    previous = {
        str(item.get("id")): item
        for item in payload.get("deduplicatedObjects", [])
        if isinstance(item, dict) and item.get("id")
    }
    payload.update({
        "sceneId": snapshot.sceneId,
        "status": "user_customized",
        "deduplicatedObjects": [
            _merge_object(previous.get(item.instanceId, {}), item, order)
            for order, item in enumerate(snapshot.objects)
        ],
        "userContext": snapshot.userContext.model_dump(mode="json"),
        "userSnapshot": snapshot.model_dump(mode="json"),
        "updatedAt": snapshot.updatedAt,
    })
    payload["userData"] = {
        **(payload.get("userData") if isinstance(payload.get("userData"), dict) else {}),
        "baseExport": str(base_path.relative_to(BACKEND_ROOT)).replace(os.sep, "/") if base_path.is_file() else None,
        "userId": user_id,
    }
    if user_requirements is not None:
        payload["userRequirements"] = user_requirements

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, target)
    return target


def load_user_floorplan(scene_id: str, user_id: str = DEMO_USER_ID) -> dict[str, Any]:
    path = user_floorplan_path(scene_id, user_id)
    if not path.is_file():
        raise FileNotFoundError(f"User floorplan not found: {scene_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_advice_result(
    scene_id: str, result: dict[str, Any], user_id: str = DEMO_USER_ID
) -> Path:
    target = user_floorplan_path(scene_id, user_id)
    payload = load_user_floorplan(scene_id, user_id)
    payload["skillAdvice"] = result
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, target)
    return target
