from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.floorplan_whitebox.whitebox_builder import build_whitebox_glb, load_scene


def read_glb_document(path: Path) -> dict:
    payload = path.read_bytes()
    if payload[:4] != b"glTF":
        raise AssertionError("Generated file is not a GLB")
    json_length, json_type = struct.unpack_from("<I4s", payload, 12)
    if json_type != b"JSON":
        raise AssertionError("GLB JSON chunk is missing")
    return json.loads(payload[20 : 20 + json_length].decode("utf-8"))


def assert_section_metadata(path: Path, expected_walls: int, expected_fixtures: int) -> None:
    document = read_glb_document(path)
    wall_nodes = [
        node
        for node in document["nodes"]
        if node.get("extras", {}).get("rombotKind") == "wall"
    ]
    fixture_nodes = [
        node
        for node in document["nodes"]
        if node.get("extras", {}).get("rombotKind") == "fixture"
    ]
    wall_ids = {node["extras"]["wallId"] for node in wall_nodes}
    fixture_ids = {node["extras"]["fixtureId"] for node in fixture_nodes}
    assert len(wall_ids) == expected_walls
    assert len(fixture_ids) == expected_fixtures
    assert all("wallStart" in node["extras"] for node in wall_nodes)
    assert all("wallEnd" in node["extras"] for node in wall_nodes)
    assert all(node["extras"].get("wallId") for node in fixture_nodes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a floorplan whitebox GLB from normalized JSON.")
    parser.add_argument(
        "scene_json",
        nargs="?",
        default=str(BACKEND_ROOT / "sample_data" / "floorplans" / "sample_whitebox_scene.json"),
        help="Path to normalized floorplan scene JSON.",
    )
    parser.add_argument(
        "--output",
        default=str(BACKEND_ROOT / "outputs" / "floorplans" / "sample_floorplan_whitebox" / "whitebox.glb"),
        help="Path for the generated GLB.",
    )
    args = parser.parse_args()

    scene_path = Path(args.scene_json).resolve()
    output_path = Path(args.output).resolve()
    scene = load_scene(scene_path)
    build_whitebox_glb(scene, output_path)
    assert_section_metadata(output_path, len(scene.walls), len(scene.wallFixtures))

    print(f"scene: {scene.sceneId}")
    print(f"walls: {len(scene.walls)}")
    print(f"fixtures: {len(scene.wallFixtures)}")
    print(f"glb: {output_path}")
    print(f"bytes: {output_path.stat().st_size}")
    print("section metadata: PASS")


if __name__ == "__main__":
    main()
