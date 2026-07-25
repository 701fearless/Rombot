from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.floorplan_whitebox.schemas import FloorplanWhiteboxScene, WallFixture, WhiteboxWall


FIXED_WALL_HEIGHT = 3.0
FIXED_WALL_THICKNESS = 0.1
FLOOR_THICKNESS = 0.03
SURFACE_EPSILON = 0.012
DOOR_FRAME_WIDTH = 0.08
WINDOW_FRAME_WIDTH = 0.07
MIN_WALL_BLOCK_SIZE = 0.04
MIN_FIXTURE_WIDTH = 0.06


@dataclass(frozen=True)
class Basis:
    start: tuple[float, float]
    end: tuple[float, float]
    length: float
    ux: float
    uz: float
    nx: float
    nz: float


@dataclass
class Primitive:
    name: str
    positions: list[tuple[float, float, float]]
    normals: list[tuple[float, float, float]]
    indices: list[int]
    material: str
    extras: dict[str, Any] | None = None


@dataclass(frozen=True)
class FixtureMetrics:
    center_u: float
    visual_width: float
    cut_width: float
    bottom: float
    top: float
    frame_width: float


MATERIALS: dict[str, dict[str, Any]] = {
    "floor": {"baseColorFactor": [0.72, 0.72, 0.68, 1.0], "roughnessFactor": 0.85},
    "wall": {"baseColorFactor": [0.92, 0.9, 0.84, 1.0], "roughnessFactor": 0.8},
    "trim": {"baseColorFactor": [0.97, 0.96, 0.92, 1.0], "roughnessFactor": 0.7},
    "door": {"baseColorFactor": [0.62, 0.5, 0.38, 1.0], "roughnessFactor": 0.72},
    "metal": {"baseColorFactor": [0.78, 0.69, 0.48, 1.0], "metallicFactor": 0.6, "roughnessFactor": 0.35},
    "glass": {"baseColorFactor": [0.58, 0.82, 0.95, 0.38], "roughnessFactor": 0.05, "alphaMode": "BLEND"},
}


def build_whitebox_glb(scene: FloorplanWhiteboxScene, output_path: Path) -> Path:
    primitives = build_whitebox_primitives(scene)
    writer = GlbWriter(primitives)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write(output_path)
    return output_path


def build_whitebox_primitives(scene: FloorplanWhiteboxScene) -> list[Primitive]:
    wall_by_id = {wall.id: wall for wall in scene.walls}
    fixtures_by_wall: dict[str, list[WallFixture]] = {}
    for fixture in scene.wallFixtures:
        fixtures_by_wall.setdefault(fixture.wallId, []).append(fixture)

    primitives: list[Primitive] = []
    floor = build_floor(scene.floorPolygon)
    floor.extras = {"rombotKind": "floor"}
    primitives.append(floor)

    for wall in scene.walls:
        wall_primitives = build_wall_blocks(wall, fixtures_by_wall.get(wall.id, []))
        for primitive in wall_primitives:
            primitive.extras = {
                "rombotKind": "wall",
                "wallId": wall.id,
                "wallStart": list(wall.start),
                "wallEnd": list(wall.end),
            }
        primitives.extend(wall_primitives)

    for fixture in scene.wallFixtures:
        wall = wall_by_id.get(fixture.wallId)
        if wall is None:
            continue
        fixture_primitives: list[Primitive] = []
        if fixture.type == "door":
            fixture_primitives = build_door(wall, fixture)
        elif fixture.type == "window":
            fixture_primitives = build_window(wall, fixture)
        for primitive in fixture_primitives:
            primitive.extras = {
                "rombotKind": "fixture",
                "fixtureId": fixture.id,
                "wallId": fixture.wallId,
            }
        primitives.extend(fixture_primitives)

    return primitives


def load_scene(path: Path) -> FloorplanWhiteboxScene:
    return FloorplanWhiteboxScene.model_validate_json(path.read_text(encoding="utf-8-sig"))


def wall_basis(wall: WhiteboxWall) -> Basis:
    sx, sz = wall.start
    ex, ez = wall.end
    dx = ex - sx
    dz = ez - sz
    length = math.hypot(dx, dz)
    if length <= 0:
        raise ValueError(f"Wall {wall.id} has zero length")
    ux = dx / length
    uz = dz / length
    return Basis(start=wall.start, end=wall.end, length=length, ux=ux, uz=uz, nx=-uz, nz=ux)


def build_floor(points: list[tuple[float, float]]) -> Primitive:
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_z = min(point[1] for point in points)
    max_z = max(point[1] for point in points)
    return oriented_box(
        name="floor",
        center=(min_x + (max_x - min_x) / 2, -FLOOR_THICKNESS / 2, min_z + (max_z - min_z) / 2),
        axis_u=(1, 0),
        axis_n=(0, 1),
        size_u=max_x - min_x,
        size_n=max_z - min_z,
        size_y=FLOOR_THICKNESS,
        material="floor",
    )


def build_wall(wall: WhiteboxWall) -> Primitive:
    basis = wall_basis(wall)
    center = (
        wall.start[0] + basis.ux * basis.length / 2,
        FIXED_WALL_HEIGHT / 2,
        wall.start[1] + basis.uz * basis.length / 2,
    )
    return oriented_box(
        name=wall.id,
        center=center,
        axis_u=(basis.ux, basis.uz),
        axis_n=(basis.nx, basis.nz),
        size_u=basis.length,
        size_n=FIXED_WALL_THICKNESS,
        size_y=FIXED_WALL_HEIGHT,
        material="wall",
    )


def build_wall_blocks(wall: WhiteboxWall, fixtures: list[WallFixture]) -> list[Primitive]:
    if not fixtures:
        return [build_wall(wall)]

    basis = wall_basis(wall)
    metrics = [fixture_metrics(basis, fixture) for fixture in fixtures]
    u_coords = [0.0, basis.length]
    y_coords = [0.0, FIXED_WALL_HEIGHT]
    for metric in metrics:
        u_coords.extend([metric.center_u - metric.cut_width / 2, metric.center_u + metric.cut_width / 2])
        y_coords.extend([metric.bottom, metric.top])

    u_coords = sorted_unique_clamped(u_coords, 0.0, basis.length)
    y_coords = sorted_unique_clamped(y_coords, 0.0, FIXED_WALL_HEIGHT)
    blocks: list[Primitive] = []

    for u_index, (u0, u1) in enumerate(pairwise(u_coords), start=1):
        if u1 - u0 < MIN_WALL_BLOCK_SIZE:
            continue
        for y_index, (y0, y1) in enumerate(pairwise(y_coords), start=1):
            if y1 - y0 < MIN_WALL_BLOCK_SIZE:
                continue
            u_mid = (u0 + u1) / 2
            y_mid = (y0 + y1) / 2
            if any(
                metric.center_u - metric.cut_width / 2 < u_mid < metric.center_u + metric.cut_width / 2
                and metric.bottom < y_mid < metric.top
                for metric in metrics
            ):
                continue
            center_x, center_z = point_at_u(basis, u_mid)
            blocks.append(
                oriented_box(
                    name=f"{wall.id}_block_{u_index:02d}_{y_index:02d}",
                    center=(center_x, y_mid, center_z),
                    axis_u=(basis.ux, basis.uz),
                    axis_n=(basis.nx, basis.nz),
                    size_u=u1 - u0,
                    size_n=FIXED_WALL_THICKNESS,
                    size_y=y1 - y0,
                    material="wall",
                )
            )
    return blocks


def build_door(wall: WhiteboxWall, fixture: WallFixture) -> list[Primitive]:
    basis = wall_basis(wall)
    metric = fixture_metrics(basis, fixture)
    center_x, center_z = point_at_u(basis, metric.center_u)
    bottom = metric.bottom
    height = metric.top - metric.bottom
    y_center = bottom + height / 2
    style = fixture.style.lower()
    door_parts: list[Primitive] = []

    if "sliding" in style:
        panel_width = metric.visual_width * 0.54
        panel_height = height * 0.96
        panel_y = bottom + panel_height / 2
        overlap = panel_width * 0.18
        for index, (along, normal_offset) in enumerate(
            [(-(panel_width - overlap) / 2, -0.018), ((panel_width - overlap) / 2, 0.018)],
            start=1,
        ):
            door_parts.append(
                oriented_box(
                    name=f"{fixture.id}_sliding_panel_{index}",
                    center=offset_center(center_x, center_z, basis, along, normal_offset),
                    axis_u=(basis.ux, basis.uz),
                    axis_n=(basis.nx, basis.nz),
                    size_u=panel_width,
                    size_n=0.028,
                    size_y=panel_height,
                    material="glass",
                    center_y=panel_y,
                )
            )
        for rail_y, rail_name in [(bottom + 0.04, "bottom_track"), (bottom + height - 0.04, "top_track")]:
            door_parts.append(
                oriented_box(
                    name=f"{fixture.id}_{rail_name}",
                    center=(center_x, rail_y, center_z),
                    axis_u=(basis.ux, basis.uz),
                    axis_n=(basis.nx, basis.nz),
                    size_u=metric.visual_width,
                    size_n=FIXED_WALL_THICKNESS + 0.06,
                    size_y=0.035,
                    material="metal",
                )
            )
        for index, along in enumerate([-metric.visual_width * 0.16, metric.visual_width * 0.16], start=1):
            door_parts.append(
                oriented_box(
                    name=f"{fixture.id}_sliding_pull_{index}",
                    center=offset_center(center_x, center_z, basis, along, FIXED_WALL_THICKNESS / 2 + 0.035),
                    axis_u=(basis.ux, basis.uz),
                    axis_n=(basis.nx, basis.nz),
                    size_u=0.045,
                    size_n=0.045,
                    size_y=0.34,
                    material="metal",
                    center_y=min(1.05, bottom + height * 0.52),
                )
            )
    elif any(token in style for token in ("swing", "hinged", "rotating", "revolving", "pivot")):
        panel_width = metric.visual_width * 0.88
        side_sign = 1 if fixture.side == "front" else -1
        angle = math.radians(58 * side_sign)
        door_ux = basis.ux * math.cos(angle) + basis.nx * math.sin(angle)
        door_uz = basis.uz * math.cos(angle) + basis.nz * math.sin(angle)
        door_nx = -door_uz
        door_nz = door_ux
        hinge_u = -metric.visual_width / 2 + metric.frame_width
        hinge_x = center_x + basis.ux * hinge_u
        hinge_z = center_z + basis.uz * hinge_u
        panel_center = (
            hinge_x + door_ux * panel_width / 2,
            y_center,
            hinge_z + door_uz * panel_width / 2,
        )
        door_parts.append(
            oriented_box(
                name=f"{fixture.id}_swing_panel",
                center=panel_center,
                axis_u=(door_ux, door_uz),
                axis_n=(door_nx, door_nz),
                size_u=panel_width,
                size_n=0.045,
                size_y=height,
                material="door",
            )
        )
        door_parts.append(
            oriented_box(
                name=f"{fixture.id}_hinge_post",
                center=(hinge_x, y_center, hinge_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=0.04,
                size_n=FIXED_WALL_THICKNESS + 0.07,
                size_y=height,
                material="metal",
            )
        )
        handle_x = hinge_x + door_ux * (panel_width - 0.12)
        handle_z = hinge_z + door_uz * (panel_width - 0.12)
        door_parts.append(
            oriented_box(
                name=f"{fixture.id}_swing_handle",
                center=(handle_x, min(1.05, bottom + height * 0.52), handle_z),
                axis_u=(door_ux, door_uz),
                axis_n=(door_nx, door_nz),
                size_u=0.055,
                size_n=0.055,
                size_y=0.12,
                material="metal",
            )
        )
    else:
        door_parts.append(
            oriented_box(
                name=f"{fixture.id}_panel",
                center=(center_x, y_center, center_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=metric.visual_width * 0.88,
                size_n=0.045,
                size_y=height,
                material="door",
            )
        )

    frame_depth = FIXED_WALL_THICKNESS + 0.08
    frame_width = metric.frame_width
    frame_height = min(FIXED_WALL_HEIGHT, height + frame_width)
    outer_width = metric.cut_width
    frame_y = bottom + frame_height / 2

    left = oriented_box(
        name=f"{fixture.id}_frame_left",
        center=offset_center(center_x, center_z, basis, -outer_width / 2 + frame_width / 2, 0.0),
        axis_u=(basis.ux, basis.uz),
        axis_n=(basis.nx, basis.nz),
        size_u=frame_width,
        size_n=frame_depth,
        size_y=frame_height,
        material="trim",
        center_y=frame_y,
    )
    right = oriented_box(
        name=f"{fixture.id}_frame_right",
        center=offset_center(center_x, center_z, basis, outer_width / 2 - frame_width / 2, 0.0),
        axis_u=(basis.ux, basis.uz),
        axis_n=(basis.nx, basis.nz),
        size_u=frame_width,
        size_n=frame_depth,
        size_y=frame_height,
        material="trim",
        center_y=frame_y,
    )
    top = oriented_box(
        name=f"{fixture.id}_frame_top",
        center=(center_x, bottom + frame_height - frame_width / 2, center_z),
        axis_u=(basis.ux, basis.uz),
        axis_n=(basis.nx, basis.nz),
        size_u=outer_width,
        size_n=frame_depth,
        size_y=frame_width,
        material="trim",
    )

    handles: list[Primitive] = []
    if not ("sliding" in style or any(token in style for token in ("swing", "hinged", "rotating", "revolving", "pivot"))):
        handle_side = min(metric.visual_width * 0.34, max(0.08, metric.visual_width / 2 - 0.08))
        handle_y = min(1.05, bottom + height * 0.52)
        handles = [
            oriented_box(
                name=f"{fixture.id}_handle_front",
                center=(
                    center_x + basis.ux * handle_side + basis.nx * (FIXED_WALL_THICKNESS / 2 + 0.035),
                    handle_y,
                    center_z + basis.uz * handle_side + basis.nz * (FIXED_WALL_THICKNESS / 2 + 0.035),
                ),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=0.055,
                size_n=0.055,
                size_y=0.12,
                material="metal",
            ),
            oriented_box(
                name=f"{fixture.id}_handle_back",
                center=(
                    center_x + basis.ux * handle_side - basis.nx * (FIXED_WALL_THICKNESS / 2 + 0.035),
                    handle_y,
                    center_z + basis.uz * handle_side - basis.nz * (FIXED_WALL_THICKNESS / 2 + 0.035),
                ),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=0.055,
                size_n=0.055,
                size_y=0.12,
                material="metal",
            ),
        ]

    return [*door_parts, left, right, top, *handles]


def build_window(wall: WhiteboxWall, fixture: WallFixture) -> list[Primitive]:
    basis = wall_basis(wall)
    metric = fixture_metrics(basis, fixture)
    center_x, center_z = point_at_u(basis, metric.center_u)
    bottom = metric.bottom
    height = metric.top - metric.bottom
    y_center = bottom + height / 2
    frame_width = metric.frame_width
    frame_depth = FIXED_WALL_THICKNESS + 0.08
    outer_width = metric.cut_width
    outer_height = height + frame_width * 2
    frame_y = bottom + height / 2

    glass = oriented_box(
        name=f"{fixture.id}_glass",
        center=(center_x, y_center, center_z),
        axis_u=(basis.ux, basis.uz),
        axis_n=(basis.nx, basis.nz),
        size_u=metric.visual_width * 0.92,
        size_n=0.024,
        size_y=height * 0.88,
        material="glass",
    )

    parts = [glass]
    parts.extend(
        [
            oriented_box(
                name=f"{fixture.id}_frame_left",
                center=offset_center(center_x, center_z, basis, -outer_width / 2 + frame_width / 2, 0.0),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=frame_width,
                size_n=frame_depth,
                size_y=outer_height,
                material="trim",
                center_y=frame_y,
            ),
            oriented_box(
                name=f"{fixture.id}_frame_right",
                center=offset_center(center_x, center_z, basis, outer_width / 2 - frame_width / 2, 0.0),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=frame_width,
                size_n=frame_depth,
                size_y=outer_height,
                material="trim",
                center_y=frame_y,
            ),
            oriented_box(
                name=f"{fixture.id}_frame_top",
                center=(center_x, bottom + height + frame_width / 2, center_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=outer_width,
                size_n=frame_depth,
                size_y=frame_width,
                material="trim",
            ),
            oriented_box(
                name=f"{fixture.id}_frame_bottom",
                center=(center_x, bottom - frame_width / 2, center_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=outer_width,
                size_n=frame_depth,
                size_y=frame_width,
                material="trim",
            ),
            oriented_box(
                name=f"{fixture.id}_mullion_vertical",
                center=(center_x, y_center, center_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=0.045,
                size_n=frame_depth,
                size_y=height,
                material="trim",
            ),
            oriented_box(
                name=f"{fixture.id}_mullion_horizontal",
                center=(center_x, y_center, center_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=metric.visual_width,
                size_n=frame_depth,
                size_y=0.045,
                material="trim",
            ),
            oriented_box(
                name=f"{fixture.id}_sill",
                center=(center_x, bottom - 0.11, center_z),
                axis_u=(basis.ux, basis.uz),
                axis_n=(basis.nx, basis.nz),
                size_u=outer_width + 0.18,
                size_n=FIXED_WALL_THICKNESS + 0.18,
                size_y=0.08,
                material="trim",
            ),
        ]
    )
    return parts


def fixture_metrics(basis: Basis, fixture: WallFixture) -> FixtureMetrics:
    frame_width = DOOR_FRAME_WIDTH if fixture.type == "door" else WINDOW_FRAME_WIDTH
    margin = MIN_WALL_BLOCK_SIZE
    max_cut_width = max(MIN_FIXTURE_WIDTH, basis.length - margin * 2)
    requested_cut_width = fixture.width + frame_width * 2
    cut_width = min(requested_cut_width, max_cut_width, basis.length)
    visual_width = max(MIN_FIXTURE_WIDTH, cut_width - frame_width * 2)
    if cut_width >= basis.length:
        center_u = basis.length / 2
    else:
        min_center = cut_width / 2 + margin
        max_center = basis.length - cut_width / 2 - margin
        center_u = clamp(fixture.offset, min_center, max_center)

    bottom = clamp(fixture.bottom, 0.0, FIXED_WALL_HEIGHT - 0.1)
    top = clamp(fixture.bottom + fixture.height, bottom + 0.1, FIXED_WALL_HEIGHT)
    return FixtureMetrics(
        center_u=center_u,
        visual_width=visual_width,
        cut_width=cut_width,
        bottom=bottom,
        top=top,
        frame_width=frame_width,
    )


def point_at_u(basis: Basis, offset: float) -> tuple[float, float]:
    return basis.start[0] + basis.ux * offset, basis.start[1] + basis.uz * offset


def clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        return (minimum + maximum) / 2
    return max(minimum, min(value, maximum))


def sorted_unique_clamped(values: list[float], minimum: float, maximum: float) -> list[float]:
    result: list[float] = []
    for value in sorted(clamp(item, minimum, maximum) for item in values):
        if not result or abs(value - result[-1]) >= 1e-6:
            result.append(value)
    return result


def pairwise(values: list[float]):
    return zip(values, values[1:])


def offset_center(
    center_x: float,
    center_z: float,
    basis: Basis,
    along_wall: float,
    normal_offset: float,
) -> tuple[float, float, float]:
    return (
        center_x + basis.ux * along_wall + basis.nx * normal_offset,
        0,
        center_z + basis.uz * along_wall + basis.nz * normal_offset,
    )


def oriented_box(
    name: str,
    center: tuple[float, float, float],
    axis_u: tuple[float, float],
    axis_n: tuple[float, float],
    size_u: float,
    size_n: float,
    size_y: float,
    material: str,
    center_y: float | None = None,
) -> Primitive:
    cx, cy, cz = center
    if center_y is not None:
        cy = center_y
    ux, uz = axis_u
    nx, nz = axis_n
    hu = size_u / 2
    hn = size_n / 2
    hy = size_y / 2

    def point(u: float, y: float, n: float) -> tuple[float, float, float]:
        return (cx + ux * u + nx * n, cy + y, cz + uz * u + nz * n)

    corners = {
        "lbf": point(-hu, -hy, hn),
        "rbf": point(hu, -hy, hn),
        "rtf": point(hu, hy, hn),
        "ltf": point(-hu, hy, hn),
        "lbb": point(-hu, -hy, -hn),
        "rbb": point(hu, -hy, -hn),
        "rtb": point(hu, hy, -hn),
        "ltb": point(-hu, hy, -hn),
    }
    faces = [
        (["lbf", "rbf", "rtf", "ltf"], (nx, 0, nz)),
        (["rbb", "lbb", "ltb", "rtb"], (-nx, 0, -nz)),
        (["rbf", "rbb", "rtb", "rtf"], (ux, 0, uz)),
        (["lbb", "lbf", "ltf", "ltb"], (-ux, 0, -uz)),
        (["ltf", "rtf", "rtb", "ltb"], (0, 1, 0)),
        (["lbb", "rbb", "rbf", "lbf"], (0, -1, 0)),
    ]

    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    for face, normal in faces:
        start = len(positions)
        positions.extend(corners[key] for key in face)
        normals.extend([normal] * 4)
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])
    return Primitive(name=name, positions=positions, normals=normals, indices=indices, material=material)


class GlbWriter:
    def __init__(self, primitives: list[Primitive]) -> None:
        self.primitives = primitives
        self.binary = bytearray()
        self.buffer_views: list[dict[str, Any]] = []
        self.accessors: list[dict[str, Any]] = []

    def write(self, output_path: Path) -> None:
        materials = self.build_materials()
        material_index = {material["name"]: index for index, material in enumerate(materials)}
        meshes = []
        nodes = []

        for primitive in self.primitives:
            position_accessor = self.add_float_accessor(primitive.positions, "VEC3", target=34962)
            normal_accessor = self.add_float_accessor(primitive.normals, "VEC3", target=34962)
            index_accessor = self.add_index_accessor(primitive.indices)
            mesh_index = len(meshes)
            meshes.append(
                {
                    "name": primitive.name,
                    "primitives": [
                        {
                            "attributes": {"POSITION": position_accessor, "NORMAL": normal_accessor},
                            "indices": index_accessor,
                            "material": material_index[primitive.material],
                        }
                    ],
                }
            )
            node = {"name": primitive.name, "mesh": mesh_index}
            if primitive.extras:
                node["extras"] = primitive.extras
            nodes.append(node)

        document = {
            "asset": {"version": "2.0", "generator": "Rombot floorplan whitebox builder"},
            "scene": 0,
            "scenes": [{"nodes": list(range(len(nodes)))}],
            "nodes": nodes,
            "meshes": meshes,
            "materials": materials,
            "buffers": [{"byteLength": len(self.binary)}],
            "bufferViews": self.buffer_views,
            "accessors": self.accessors,
        }
        write_glb(output_path, document, bytes(self.binary))

    def build_materials(self) -> list[dict[str, Any]]:
        result = []
        for name, source in MATERIALS.items():
            material = {
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": source["baseColorFactor"],
                    "metallicFactor": source.get("metallicFactor", 0.0),
                    "roughnessFactor": source.get("roughnessFactor", 0.75),
                },
            }
            if "alphaMode" in source:
                material["alphaMode"] = source["alphaMode"]
                material["doubleSided"] = True
            result.append(material)
        return result

    def add_float_accessor(self, values: list[tuple[float, float, float]], accessor_type: str, target: int) -> int:
        offset = self.append_aligned(b"".join(struct.pack("<fff", *value) for value in values))
        view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(values) * 12, "target": target})
        accessor_index = len(self.accessors)
        mins = [min(value[i] for value in values) for i in range(3)]
        maxs = [max(value[i] for value in values) for i in range(3)]
        self.accessors.append(
            {
                "bufferView": view_index,
                "componentType": 5126,
                "count": len(values),
                "type": accessor_type,
                "min": mins,
                "max": maxs,
            }
        )
        return accessor_index

    def add_index_accessor(self, values: list[int]) -> int:
        offset = self.append_aligned(b"".join(struct.pack("<H", value) for value in values))
        view_index = len(self.buffer_views)
        self.buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(values) * 2, "target": 34963})
        accessor_index = len(self.accessors)
        self.accessors.append(
            {
                "bufferView": view_index,
                "componentType": 5123,
                "count": len(values),
                "type": "SCALAR",
                "min": [min(values)],
                "max": [max(values)],
            }
        )
        return accessor_index

    def append_aligned(self, payload: bytes) -> int:
        while len(self.binary) % 4:
            self.binary.append(0)
        offset = len(self.binary)
        self.binary.extend(payload)
        while len(self.binary) % 4:
            self.binary.append(0)
        return offset


def write_glb(output_path: Path, document: dict[str, Any], binary: bytes) -> None:
    json_chunk = json.dumps(document, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    while len(json_chunk) % 4:
        json_chunk += b" "
    while len(binary) % 4:
        binary += b"\x00"
    total_length = 12 + 8 + len(json_chunk) + 8 + len(binary)
    with output_path.open("wb") as file:
        file.write(struct.pack("<III", 0x46546C67, 2, total_length))
        file.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        file.write(json_chunk)
        file.write(struct.pack("<I4s", len(binary), b"BIN\x00"))
        file.write(binary)
