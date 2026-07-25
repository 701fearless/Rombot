"""2D footprint geometry on the XZ floor plane (Y-up, meters).

Object position is the AABB/OBB center. size = [width, height, depth].
rotation[1] is yaw in radians around Y.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


SIDE_OFFSETS = {
    "front": (0.0, -1.0),
    "back": (0.0, 1.0),
    "left": (-1.0, 0.0),
    "right": (1.0, 0.0),
}


@dataclass(frozen=True)
class Vec2:
    x: float
    z: float

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.z + other.z)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.z - other.z)

    def __mul__(self, scale: float) -> "Vec2":
        return Vec2(self.x * scale, self.z * scale)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.z * other.z

    def length(self) -> float:
        return math.hypot(self.x, self.z)

    def normalized(self) -> "Vec2":
        length = self.length()
        if length < 1e-9:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / length, self.z / length)


@dataclass(frozen=True)
class OrientedRect:
    """Axis-aligned in local space, rotated by yaw around Y."""

    center: Vec2
    half_width: float
    half_depth: float
    yaw: float = 0.0

    @classmethod
    def from_center_size(
        cls,
        position: list[float],
        size: list[float],
        rotation: list[float] | None = None,
    ) -> "OrientedRect":
        yaw = float(rotation[1]) if rotation and len(rotation) >= 2 else 0.0
        return cls(
            center=Vec2(float(position[0]), float(position[2])),
            half_width=max(0.0, float(size[0]) * 0.5),
            half_depth=max(0.0, float(size[2]) * 0.5),
            yaw=yaw,
        )

    def local_axes(self) -> tuple[Vec2, Vec2]:
        cos_y = math.cos(self.yaw)
        sin_y = math.sin(self.yaw)
        axis_x = Vec2(cos_y, -sin_y)
        axis_z = Vec2(sin_y, cos_y)
        return axis_x, axis_z

    def corners(self) -> list[Vec2]:
        axis_x, axis_z = self.local_axes()
        offsets = (
            axis_x * self.half_width + axis_z * self.half_depth,
            axis_x * (-self.half_width) + axis_z * self.half_depth,
            axis_x * (-self.half_width) + axis_z * (-self.half_depth),
            axis_x * self.half_width + axis_z * (-self.half_depth),
        )
        return [self.center + offset for offset in offsets]

    def project(self, axis: Vec2) -> tuple[float, float]:
        corners = self.corners()
        dots = [corner.dot(axis) for corner in corners]
        return min(dots), max(dots)

    def intersects(self, other: "OrientedRect", epsilon: float = 1e-6) -> bool:
        axes = list(self.local_axes()) + list(other.local_axes())
        for axis in axes:
            if axis.length() < 1e-9:
                continue
            unit = axis.normalized()
            min_a, max_a = self.project(unit)
            min_b, max_b = other.project(unit)
            if max_a < min_b - epsilon or max_b < min_a - epsilon:
                return False
        return True

    def aabb(self) -> "Aabb2":
        corners = self.corners()
        xs = [c.x for c in corners]
        zs = [c.z for c in corners]
        return Aabb2(min(xs), min(zs), max(xs), max(zs))

    def world_direction(self, local_dir: tuple[float, float]) -> Vec2:
        axis_x, axis_z = self.local_axes()
        return (axis_x * local_dir[0] + axis_z * local_dir[1]).normalized()

    def clearance_zone(self, side: str, distance: float) -> "OrientedRect":
        """Build a rectangle adjacent to one side, used for activity clearance."""
        if distance <= 0:
            return OrientedRect(self.center, 0.0, 0.0, self.yaw)

        local = SIDE_OFFSETS[side]
        direction = self.world_direction(local)
        if side in ("front", "back"):
            half_w = self.half_width
            half_d = distance * 0.5
            # Zone center sits just outside the furniture face along front/back.
            offset = direction * (self.half_depth + half_d)
            # Local front/back zone: width along X, depth along Z of oriented frame.
            # Align zone yaw with furniture; for front/back the "depth" of zone is along local Z.
            return OrientedRect(
                center=self.center + offset,
                half_width=half_w,
                half_depth=half_d,
                yaw=self.yaw,
            )

        half_w = distance * 0.5
        half_d = self.half_depth
        offset = direction * (self.half_width + half_w)
        return OrientedRect(
            center=self.center + offset,
            half_width=half_w,
            half_depth=half_d,
            yaw=self.yaw,
        )


@dataclass(frozen=True)
class Aabb2:
    min_x: float
    min_z: float
    max_x: float
    max_z: float

    @classmethod
    def from_room(cls, width: float, depth: float) -> "Aabb2":
        return cls(0.0, 0.0, float(width), float(depth))

    def contains_rect(self, rect: OrientedRect, epsilon: float = 1e-6) -> bool:
        box = rect.aabb()
        return (
            box.min_x >= self.min_x - epsilon
            and box.min_z >= self.min_z - epsilon
            and box.max_x <= self.max_x + epsilon
            and box.max_z <= self.max_z + epsilon
        )

    def clamp_overflow(self, rect: OrientedRect) -> dict[str, float]:
        box = rect.aabb()
        return {
            "left": max(0.0, self.min_x - box.min_x),
            "right": max(0.0, box.max_x - self.max_x),
            "back": max(0.0, box.max_z - self.max_z),
            "front": max(0.0, self.min_z - box.min_z),
        }

    def intersects_rect(self, rect: OrientedRect) -> bool:
        return self.as_rect().intersects(rect)

    def as_rect(self) -> OrientedRect:
        return OrientedRect(
            center=Vec2((self.min_x + self.max_x) * 0.5, (self.min_z + self.max_z) * 0.5),
            half_width=(self.max_x - self.min_x) * 0.5,
            half_depth=(self.max_z - self.min_z) * 0.5,
            yaw=0.0,
        )


def overlap_depth_m(a: OrientedRect, b: OrientedRect) -> float:
    """Approximate penetration depth using AABB overlap on XZ."""
    aa = a.aabb()
    bb = b.aabb()
    overlap_x = min(aa.max_x, bb.max_x) - max(aa.min_x, bb.min_x)
    overlap_z = min(aa.max_z, bb.max_z) - max(aa.min_z, bb.min_z)
    if overlap_x <= 0 or overlap_z <= 0:
        return 0.0
    return min(overlap_x, overlap_z)


def free_distance_along_side(
    furniture: OrientedRect,
    side: str,
    blockers: list[OrientedRect],
    room: Aabb2,
    max_probe: float = 2.0,
    step: float = 0.05,
) -> float:
    """Measure how far the side stays clear before hitting a blocker or room edge."""
    cleared = 0.0
    probe = step
    while probe <= max_probe + 1e-9:
        zone = furniture.clearance_zone(side, probe)
        if not room.contains_rect(zone):
            break
        if any(zone.intersects(blocker) for blocker in blockers):
            break
        cleared = probe
        probe += step
    return round(cleared, 3)
