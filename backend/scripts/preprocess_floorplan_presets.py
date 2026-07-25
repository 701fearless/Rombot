from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings
from app.services.floorplan_whitebox.ai_parser import ArkFloorplanParser
from app.services.floorplan_whitebox.schemas import FloorplanWhiteboxScene
from app.services.floorplan_whitebox.whitebox_builder import build_whitebox_glb
from app.storage.local_store import file_to_data_url


FLOORPLAN_ROOT = BACKEND_ROOT / "sample_data" / "floorplans"
PREPROCESSED_ROOT = FLOORPLAN_ROOT / "preprocessed"
MANIFEST_PATH = FLOORPLAN_ROOT / "presets.json"
PLACEHOLDER_SCENE_PATH = FLOORPLAN_ROOT / "sample_whitebox_scene.json"
PLACEHOLDER_GLB_PATH = FLOORPLAN_ROOT / "whitebox.glb"
DEFAULT_ROOM_IDS = [f"room{index}" for index in range(1, 8)]


def force_defaults(scene: FloorplanWhiteboxScene, scene_id: str) -> FloorplanWhiteboxScene:
    data = scene.model_dump()
    data["sceneId"] = scene_id
    data["wallHeight"] = 3.0
    data["defaultWallThickness"] = 0.1
    for wall in data["walls"]:
        wall["height"] = 3.0
        wall["thickness"] = 0.1
    return FloorplanWhiteboxScene.model_validate(data)


def source_image_path(room_id: str) -> Path:
    candidates = [
        FLOORPLAN_ROOT / f"{room_id}{suffix}"
        for suffix in (".png", ".jpg", ".jpeg", ".webp")
    ]
    match = next((path for path in candidates if path.exists()), None)
    if match is None:
        raise FileNotFoundError(f"No source image found for {room_id}")
    return match


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest_records() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records = payload.get("presets", payload)
    return {str(item["sceneId"]): item for item in records}


def write_artifacts(
    scene: FloorplanWhiteboxScene,
    room_id: str,
    *,
    use_placeholder_glb: bool,
) -> None:
    target_dir = PREPROCESSED_ROOT / room_id
    target_dir.mkdir(parents=True, exist_ok=True)
    scene_path = target_dir / "normalized_scene.json.tmp"
    glb_path = target_dir / "whitebox.glb.tmp"
    scene_path.write_text(scene.model_dump_json(indent=2), encoding="utf-8")
    if use_placeholder_glb:
        if not PLACEHOLDER_GLB_PATH.is_file():
            raise FileNotFoundError(
                f"Placeholder GLB not found: {PLACEHOLDER_GLB_PATH}"
            )
        shutil.copyfile(PLACEHOLDER_GLB_PATH, glb_path)
    else:
        build_whitebox_glb(scene, glb_path)
    scene_path.replace(target_dir / "normalized_scene.json")
    glb_path.replace(target_dir / "whitebox.glb")


async def build_ark_scene(room_id: str, image_path: Path) -> FloorplanWhiteboxScene:
    settings = get_settings()
    if not settings.ark_api_key:
        raise RuntimeError("ARK_API_KEY is required for --mode ark")
    parser = ArkFloorplanParser(
        api_key=settings.ark_api_key,
        base_url=settings.ark_base_url,
        model=settings.ark_vision_model,
        timeout_sec=settings.floorplan_ai_timeout_sec,
    )
    result = await parser.parse(file_to_data_url(image_path))
    return force_defaults(result.scene, room_id)


def build_placeholder_scene(room_id: str) -> FloorplanWhiteboxScene:
    scene = FloorplanWhiteboxScene.model_validate_json(
        PLACEHOLDER_SCENE_PATH.read_text(encoding="utf-8-sig")
    )
    return force_defaults(scene, room_id)


async def preprocess(room_ids: list[str], mode: str) -> None:
    PREPROCESSED_ROOT.mkdir(parents=True, exist_ok=True)
    records = load_manifest_records()
    failures: list[str] = []

    for room_id in room_ids:
        image_path = source_image_path(room_id)
        try:
            scene = (
                await build_ark_scene(room_id, image_path)
                if mode == "ark"
                else build_placeholder_scene(room_id)
            )
            write_artifacts(
                scene,
                room_id,
                use_placeholder_glb=mode == "placeholder",
            )
            records[room_id] = {
                "sceneId": room_id,
                "title": f"户型 {room_id.removeprefix('room')}",
                "sourceImageUrl": f"/sample_data/floorplans/{image_path.name}",
                "sourceSha256": sha256_file(image_path),
                "sceneUrl": (
                    f"/sample_data/floorplans/preprocessed/{room_id}/normalized_scene.json"
                ),
                "whiteboxGlbUrl": (
                    f"/sample_data/floorplans/preprocessed/{room_id}/whitebox.glb"
                ),
                "quality": mode,
            }
            print(f"{room_id}: {mode} ready")
        except Exception as exc:  # noqa: BLE001 - preserve prior preset on one-room failure.
            failures.append(f"{room_id}: {type(exc).__name__}: {exc}")
            print(f"{room_id}: FAILED ({type(exc).__name__}: {exc})", file=sys.stderr)

    ordered = [records[key] for key in sorted(records) if key in DEFAULT_ROOM_IDS]
    temporary_manifest = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary_manifest.write_text(
        json.dumps({"version": 1, "presets": ordered}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_manifest.replace(MANIFEST_PATH)

    if failures:
        raise RuntimeError("Some presets failed:\n" + "\n".join(failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deployable room1-room7 floorplan presets."
    )
    parser.add_argument(
        "--mode",
        choices=("placeholder", "ark"),
        default="placeholder",
        help="Use a shared local whitebox or call Ark for each source image.",
    )
    parser.add_argument(
        "--room-ids",
        nargs="+",
        default=DEFAULT_ROOM_IDS,
        help="Preset ids to rebuild.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(preprocess(args.room_ids, args.mode))
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
