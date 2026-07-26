import argparse
import json
import math
import struct
from pathlib import Path


def align4(data, pad=b"\x00"):
    return data + pad * ((4 - len(data) % 4) % 4)


def add_box(vertices, indices, center, size, angle=0.0):
    cx, cy, cz = center
    sx, sy, sz = (v / 2.0 for v in size)
    c, s = math.cos(angle), math.sin(angle)
    base = len(vertices)
    local = [
        (-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
        (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz),
    ]
    for x, y, z in local:
        vertices.append((cx + x * c - y * s, cy + x * s + y * c, cz + z))
    indices.extend(base + i for i in [
        0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7,
        0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5,
        2, 3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7,
    ])


def add_wall_piece(vertices, indices, wall, start_offset, end_offset, bottom, top):
    if end_offset <= start_offset or top <= bottom:
        return
    x1, y1 = wall["start"]
    x2, y2 = wall["end"]
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    middle = (start_offset + end_offset) / 2.0
    add_box(
        vertices,
        indices,
        (x1 + ux * middle, y1 + uy * middle, (bottom + top) / 2.0),
        (end_offset - start_offset, wall["thickness"], top - bottom),
        math.atan2(uy, ux),
    )


def build_mesh(data):
    vertices, indices = [], []
    polygon = data["floorPolygon"]
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    add_box(
        vertices,
        indices,
        ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, -0.05),
        (max(xs) - min(xs), max(ys) - min(ys), 0.1),
    )

    fixtures_by_wall = {}
    for fixture in data.get("wallFixtures", []):
        fixtures_by_wall.setdefault(fixture["wallId"], []).append(fixture)

    for wall in data["walls"]:
        x1, y1 = wall["start"]
        x2, y2 = wall["end"]
        length = math.hypot(x2 - x1, y2 - y1)
        fixtures = sorted(fixtures_by_wall.get(wall["id"], []), key=lambda f: f["offset"])
        cursor = 0.0
        for fixture in fixtures:
            left = max(0.0, fixture["offset"] - fixture["width"] / 2.0)
            right = min(length, fixture["offset"] + fixture["width"] / 2.0)
            add_wall_piece(vertices, indices, wall, cursor, left, 0.0, wall["height"])
            bottom = fixture["bottom"]
            top = bottom + fixture["height"]
            add_wall_piece(vertices, indices, wall, left, right, 0.0, bottom)
            add_wall_piece(vertices, indices, wall, left, right, top, wall["height"])
            cursor = right
        add_wall_piece(vertices, indices, wall, cursor, length, 0.0, wall["height"])
    return vertices, indices


def write_glb(vertices, indices, output_path):
    position_bytes = b"".join(struct.pack("<3f", *v) for v in vertices)
    index_bytes = b"".join(struct.pack("<I", i) for i in indices)
    binary = align4(position_bytes) + align4(index_bytes)
    mins = [min(v[i] for v in vertices) for i in range(3)]
    maxs = [max(v[i] for v in vertices) for i in range(3)]
    document = {
        "asset": {"version": "2.0", "generator": "floorplan-json-to-glb"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": "floorplan_ai_001"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "material": 0}]}],
        "materials": [{
            "name": "WallMaterial",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.82, 0.82, 0.78, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.9
            },
            "doubleSided": True
        }],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(position_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": len(align4(position_bytes)), "byteLength": len(index_bytes), "target": 34963}
        ],
        "accessors": [
            {
                "bufferView": 0, "componentType": 5126, "count": len(vertices),
                "type": "VEC3", "min": mins, "max": maxs
            },
            {
                "bufferView": 1, "componentType": 5125, "count": len(indices),
                "type": "SCALAR"
            }
        ]
    }
    json_bytes = align4(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    total_length = 12 + 8 + len(json_bytes) + 8 + len(binary)
    glb = (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes
        + struct.pack("<I4s", len(binary), b"BIN\x00") + binary
    )
    output_path.write_bytes(glb)


def main():
    parser = argparse.ArgumentParser(description="Convert floor-plan JSON to GLB.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    vertices, indices = build_mesh(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_glb(vertices, indices, args.output)
    print(f"Created {args.output} ({len(vertices)} vertices, {len(indices) // 3} triangles)")


if __name__ == "__main__":
    main()
