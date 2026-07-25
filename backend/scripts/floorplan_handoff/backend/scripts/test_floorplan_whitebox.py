from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.floorplan_whitebox.whitebox_builder import build_whitebox_glb, load_scene


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

    print(f"scene: {scene.sceneId}")
    print(f"walls: {len(scene.walls)}")
    print(f"fixtures: {len(scene.wallFixtures)}")
    print(f"glb: {output_path}")
    print(f"bytes: {output_path.stat().st_size}")


if __name__ == "__main__":
    main()
