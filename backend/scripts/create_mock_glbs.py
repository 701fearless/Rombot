import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "sample_data" / "models"


VERTICES = [
    (-0.5, 0.0, -0.5),
    (0.5, 0.0, -0.5),
    (0.5, 0.0, 0.5),
    (-0.5, 0.0, 0.5),
    (-0.5, 1.0, -0.5),
    (0.5, 1.0, -0.5),
    (0.5, 1.0, 0.5),
    (-0.5, 1.0, 0.5),
]

INDICES = [
    0,
    1,
    2,
    0,
    2,
    3,
    4,
    6,
    5,
    4,
    7,
    6,
    0,
    4,
    5,
    0,
    5,
    1,
    1,
    5,
    6,
    1,
    6,
    2,
    2,
    6,
    7,
    2,
    7,
    3,
    3,
    7,
    4,
    3,
    4,
    0,
]


def pad4(data: bytes, padding: bytes) -> bytes:
    return data + padding * ((4 - len(data) % 4) % 4)


def write_glb(path: Path, name: str, color: list[float]) -> None:
    position_bytes = b"".join(struct.pack("<3f", *vertex) for vertex in VERTICES)
    index_offset = len(position_bytes)
    index_bytes = b"".join(struct.pack("<H", index) for index in INDICES)
    binary = pad4(position_bytes + index_bytes, b"\x00")

    gltf = {
        "asset": {"version": "2.0", "generator": "space-energy-mvp"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "indices": 1,
                        "material": 0,
                    }
                ]
            }
        ],
        "materials": [{"pbrMetallicRoughness": {"baseColorFactor": color, "roughnessFactor": 0.8}}],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(position_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": index_offset, "byteLength": len(index_bytes), "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,
                "count": len(VERTICES),
                "type": "VEC3",
                "min": [-0.5, 0.0, -0.5],
                "max": [0.5, 1.0, 0.5],
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5123,
                "count": len(INDICES),
                "type": "SCALAR",
            },
        ],
    }

    json_chunk = pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = binary
    total_length = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)

    with path.open("wb") as file:
        file.write(struct.pack("<III", 0x46546C67, 2, total_length))
        file.write(struct.pack("<I4s", len(json_chunk), b"JSON"))
        file.write(json_chunk)
        file.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00"))
        file.write(bin_chunk)


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    write_glb(MODEL_DIR / "sofa.glb", "mock_sofa", [0.78, 0.68, 0.55, 1.0])
    write_glb(MODEL_DIR / "coffee_table.glb", "mock_coffee_table", [0.42, 0.28, 0.18, 1.0])
    write_glb(MODEL_DIR / "chandelier.glb", "mock_chandelier", [1.0, 0.82, 0.36, 1.0])
    write_glb(MODEL_DIR / "rug.glb", "mock_rug", [0.55, 0.22, 0.18, 1.0])


if __name__ == "__main__":
    main()
