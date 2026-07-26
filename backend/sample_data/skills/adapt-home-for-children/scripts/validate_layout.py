#!/usr/bin/env python3
"""Validate normalized residential layout JSON using dependency-free 2D checks."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable


EPSILON = 1e-8


def point(value: Any) -> tuple[float, float]:
    if isinstance(value, dict):
        return float(value["x"]), float(value["y"])
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return float(value[0]), float(value[1])
    raise ValueError(f"invalid point: {value!r}")


def polygon(value: Any) -> list[tuple[float, float]]:
    if not isinstance(value, list) or len(value) < 3:
        raise ValueError("polygon needs at least three points")
    result = [point(item) for item in value]
    if any(not math.isfinite(v) for p in result for v in p):
        raise ValueError("polygon contains non-finite coordinate")
    return result


def rectangle_corners(footprint: dict[str, Any]) -> list[tuple[float, float]]:
    x, y = float(footprint["x"]), float(footprint["y"])
    width, depth = float(footprint["width"]), float(footprint["depth"])
    if width <= 0 or depth <= 0:
        raise ValueError("rectangle width and depth must be positive")
    angle = math.radians(float(footprint.get("rotationDeg", 0)))
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    result = []
    for dx, dy in ((-width / 2, -depth / 2), (width / 2, -depth / 2),
                   (width / 2, depth / 2), (-width / 2, depth / 2)):
        result.append((x + dx * cos_a - dy * sin_a, y + dx * sin_a + dy * cos_a))
    return result


def footprint_polygon(item: dict[str, Any]) -> list[tuple[float, float]] | None:
    fp = item.get("footprint")
    if not isinstance(fp, dict):
        return None
    shape = fp.get("shape", "rectangle")
    if shape == "rectangle":
        return rectangle_corners(fp)
    if shape == "polygon":
        return polygon(fp.get("points"))
    raise ValueError(f"unsupported footprint shape: {shape}")


def on_segment(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> bool:
    cross = (p[0] - a[0]) * (b[1] - a[1]) - (p[1] - a[1]) * (b[0] - a[0])
    if abs(cross) > EPSILON:
        return False
    return (min(a[0], b[0]) - EPSILON <= p[0] <= max(a[0], b[0]) + EPSILON and
            min(a[1], b[1]) - EPSILON <= p[1] <= max(a[1], b[1]) + EPSILON)


def point_in_polygon(p: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(poly) - 1
    for i, pi in enumerate(poly):
        pj = poly[j]
        if on_segment(p, pj, pi):
            return True
        if (pi[1] > p[1]) != (pj[1] > p[1]):
            cross_x = (pj[0] - pi[0]) * (p[1] - pi[1]) / (pj[1] - pi[1]) + pi[0]
            if p[0] < cross_x:
                inside = not inside
        j = i
    return inside


def axes(poly: list[tuple[float, float]]) -> Iterable[tuple[float, float]]:
    for i, current in enumerate(poly):
        nxt = poly[(i + 1) % len(poly)]
        edge = (nxt[0] - current[0], nxt[1] - current[1])
        length = math.hypot(*edge)
        if length > EPSILON:
            yield (-edge[1] / length, edge[0] / length)


def projection(poly: list[tuple[float, float]], axis: tuple[float, float]) -> tuple[float, float]:
    values = [p[0] * axis[0] + p[1] * axis[1] for p in poly]
    return min(values), max(values)


def convex_overlap(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> bool:
    for axis in list(axes(a)) + list(axes(b)):
        amin, amax = projection(a, axis)
        bmin, bmax = projection(b, axis)
        if amax <= bmin + EPSILON or bmax <= amin + EPSILON:
            return False
    return True


def clearance_polygons(room: dict[str, Any]) -> list[tuple[str, list[tuple[float, float]]]]:
    found = []
    for key in ("doors", "windows", "fixedFixtures"):
        for feature in room.get(key, []) or []:
            feature_id = str(feature.get("id", key))
            for poly_key in ("swingPolygon", "clearancePolygon", "servicePolygon"):
                if feature.get(poly_key):
                    found.append((f"{feature_id}:{poly_key}", polygon(feature[poly_key])))
    return found


def validate(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    rooms = data.get("rooms")
    furniture = data.get("furniture")
    if not isinstance(rooms, list):
        errors.append({"code": "rooms.missing", "message": "rooms must be an array"})
        rooms = []
    if not isinstance(furniture, list):
        errors.append({"code": "furniture.missing", "message": "furniture must be an array"})
        furniture = []

    room_map: dict[str, tuple[dict[str, Any], list[tuple[float, float]] | None]] = {}
    ids: set[str] = set()
    for idx, room in enumerate(rooms):
        room_id = str(room.get("id", ""))
        if not room_id:
            errors.append({"code": "room.id", "path": f"/rooms/{idx}", "message": "room id is required"})
            continue
        if room_id in ids:
            errors.append({"code": "id.duplicate", "path": f"/rooms/{idx}/id", "message": room_id})
        ids.add(room_id)
        try:
            room_poly = polygon(room["polygon"]) if room.get("polygon") else None
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"code": "room.polygon", "path": f"/rooms/{idx}/polygon", "message": str(exc)})
            room_poly = None
        if room_poly is None:
            warnings.append({"code": "room.geometry-missing", "path": f"/rooms/{idx}", "message": "cannot verify containment"})
        room_map[room_id] = (room, room_poly)

    floor_items: list[tuple[int, dict[str, Any], list[tuple[float, float]]]] = []
    for idx, item in enumerate(furniture):
        item_id = str(item.get("id", ""))
        if not item_id:
            errors.append({"code": "furniture.id", "path": f"/furniture/{idx}", "message": "furniture id is required"})
            continue
        if item_id in ids:
            errors.append({"code": "id.duplicate", "path": f"/furniture/{idx}/id", "message": item_id})
        ids.add(item_id)
        room_id = item.get("roomId")
        if room_id not in room_map:
            errors.append({"code": "furniture.room-ref", "path": f"/furniture/{idx}/roomId", "message": f"unknown room: {room_id}"})
            continue
        try:
            item_poly = footprint_polygon(item)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append({"code": "furniture.footprint", "path": f"/furniture/{idx}/footprint", "message": str(exc)})
            continue
        if item_poly is None:
            warnings.append({"code": "furniture.geometry-missing", "path": f"/furniture/{idx}", "message": "cannot verify placement"})
            continue
        if item.get("mountType", "floor") != "floor":
            if not item.get("supportSurfaceId"):
                warnings.append({"code": "support.missing", "path": f"/furniture/{idx}", "message": "non-floor item lacks supportSurfaceId"})
            continue
        room, room_poly = room_map[room_id]
        if room_poly and not all(point_in_polygon(p, room_poly) for p in item_poly):
            errors.append({"code": "furniture.outside-room", "path": f"/furniture/{idx}", "message": item_id})
        for clearance_id, clearance_poly in clearance_polygons(room):
            if convex_overlap(item_poly, clearance_poly):
                errors.append({"code": "clearance.overlap", "path": f"/furniture/{idx}", "message": f"{item_id} overlaps {clearance_id}"})
        floor_items.append((idx, item, item_poly))

    for left in range(len(floor_items)):
        i, a, poly_a = floor_items[left]
        if a.get("allowOverlap"):
            continue
        for right in range(left + 1, len(floor_items)):
            j, b, poly_b = floor_items[right]
            if b.get("allowOverlap") or a.get("roomId") != b.get("roomId"):
                continue
            if convex_overlap(poly_a, poly_b):
                errors.append({
                    "code": "furniture.overlap",
                    "path": f"/furniture/{i}",
                    "message": f"{a.get('id')} overlaps {b.get('id')} at /furniture/{j}",
                })

    if not data.get("meta", {}).get("units"):
        warnings.append({"code": "meta.units-missing", "message": "distance and clearance semantics are uncertain"})
    if not data.get("circulationPaths"):
        warnings.append({"code": "circulation.not-proven", "message": "continuous egress and passage width were not proven"})

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "roomCount": len(rooms),
            "furnitureCount": len(furniture),
            "checkedFloorFootprints": len(floor_items),
        },
        "scope": [
            "JSON structure", "unique room/furniture ids", "room references",
            "floor footprint containment", "convex footprint overlap",
            "provided door/window/fixture clearance polygons",
        ],
        "limitations": [
            "Concave footprint overlap is not fully proven by the SAT check.",
            "Continuous walking paths and minimum width require explicit path geometry or manual review.",
            "This is not structural, electrical, fire, or accessibility certification.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        with args.layout.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("top-level JSON value must be an object")
        result = validate(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {"valid": False, "errors": [{"code": "input", "message": str(exc)}], "warnings": []}
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0 if result.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
