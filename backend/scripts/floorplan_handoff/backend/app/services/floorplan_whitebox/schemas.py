from typing import Literal

from pydantic import BaseModel, Field


Vector2 = tuple[float, float]


class WhiteboxWall(BaseModel):
    id: str
    start: Vector2
    end: Vector2
    thickness: float = 0.1
    height: float = 3.0


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
