import math
from typing import Literal

from pydantic import BaseModel, Field, model_validator


Vector2 = tuple[float, float]


class WhiteboxWall(BaseModel):
    id: str
    start: Vector2
    end: Vector2
    thickness: float = Field(default=0.1, gt=0)
    height: float = Field(default=3.0, gt=0)

    @model_validator(mode="after")
    def validate_length(self) -> "WhiteboxWall":
        if math.dist(self.start, self.end) <= 1e-6:
            raise ValueError(f"Wall {self.id!r} has zero length")
        return self


class WallFixture(BaseModel):
    id: str
    type: Literal["door", "window"]
    wallId: str
    offset: float = Field(ge=0)
    width: float = Field(gt=0)
    bottom: float = Field(default=0, ge=0)
    height: float = Field(gt=0)
    style: str = "minimal"
    side: Literal["front", "back"] = "front"


class FloorplanWhiteboxScene(BaseModel):
    sceneId: str
    unit: Literal["meter"] = "meter"
    wallHeight: float = 3.0
    defaultWallThickness: float = 0.1
    floorPolygon: list[Vector2] = Field(min_length=3)
    walls: list[WhiteboxWall] = Field(min_length=1)
    wallFixtures: list[WallFixture] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_geometry_references(self) -> "FloorplanWhiteboxScene":
        if len(set(self.floorPolygon)) < 3:
            raise ValueError("floorPolygon must contain at least three distinct points")

        wall_ids = [wall.id for wall in self.walls]
        if len(wall_ids) != len(set(wall_ids)):
            raise ValueError("Wall ids must be unique")
        fixture_ids = [fixture.id for fixture in self.wallFixtures]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("Wall fixture ids must be unique")

        walls_by_id = {wall.id: wall for wall in self.walls}
        for fixture in self.wallFixtures:
            wall = walls_by_id.get(fixture.wallId)
            if wall is None:
                raise ValueError(
                    f"Fixture {fixture.id!r} references unknown wall {fixture.wallId!r}"
                )
            wall_length = math.dist(wall.start, wall.end)
            half_width = fixture.width / 2
            if fixture.offset - half_width < -1e-6 or fixture.offset + half_width > wall_length + 1e-6:
                raise ValueError(
                    f"Fixture {fixture.id!r} does not fit inside wall {wall.id!r}"
                )
            if fixture.bottom + fixture.height > wall.height + 1e-6:
                raise ValueError(
                    f"Fixture {fixture.id!r} exceeds wall {wall.id!r} height"
                )
        return self
