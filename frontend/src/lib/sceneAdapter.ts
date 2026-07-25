import type { SceneObject, SceneOpening, SceneResponse } from "../types"

export interface NormalizedWall {
  id: string
  start: [number, number]
  end: [number, number]
  thickness?: number
  height?: number
}

export interface NormalizedFixture {
  id: string
  type: string
  wallId: string
  offset: number
  width: number
  bottom?: number
  height: number
  name?: string
  side?: string
  clearanceDepth?: number
}

export interface NormalizedScene {
  sceneId: string
  unit?: string
  wallHeight?: number
  defaultWallThickness?: number
  floorPolygon: Array<[number, number]>
  walls: NormalizedWall[]
  wallFixtures?: NormalizedFixture[]
}

const FIXTURE_LABELS: Record<string, string> = {
  door: "门",
  window: "窗",
}

function polygonExtents(polygon: Array<[number, number]>) {
  const xs = polygon.map((point) => point[0])
  const zs = polygon.map((point) => point[1])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minZ = Math.min(...zs)
  const maxZ = Math.max(...zs)
  return {
    minX,
    maxX,
    minZ,
    maxZ,
    width: Math.max(0.1, maxX - minX),
    depth: Math.max(0.1, maxZ - minZ),
  }
}

function wallById(walls: NormalizedWall[], wallId: string) {
  return walls.find((wall) => wall.id === wallId) ?? null
}

function fixtureToOpening(
  fixture: NormalizedFixture,
  walls: NormalizedWall[],
  wallHeight: number,
): SceneOpening | null {
  const wall = wallById(walls, fixture.wallId)
  if (!wall) return null

  const dx = wall.end[0] - wall.start[0]
  const dz = wall.end[1] - wall.start[1]
  const length = Math.hypot(dx, dz) || 1
  const ux = dx / length
  const uz = dz / length
  const nx = -uz
  const nz = ux
  const along = fixture.offset + fixture.width * 0.5
  const thickness = wall.thickness ?? 0.1
  const height = fixture.height
  const bottom = fixture.bottom ?? 0
  const sideSign = fixture.side === "back" ? -1 : 1

  const x = wall.start[0] + ux * along + nx * sideSign * (thickness * 0.5)
  const z = wall.start[1] + uz * along + nz * sideSign * (thickness * 0.5)
  const y = bottom + height * 0.5
  const yaw = Math.atan2(ux, uz)

  return {
    id: fixture.id,
    type: fixture.type === "window" ? "window" : "door",
    name: fixture.name || FIXTURE_LABELS[fixture.type] || fixture.id,
    position: [round3(x), round3(y), round3(z)],
    rotation: [0, round3(yaw), 0],
    size: [fixture.width, height, Math.max(thickness, 0.08)],
    clearanceDepth:
      fixture.clearanceDepth ?? (fixture.type === "window" ? 0.45 : 0.9),
  }
}

function round3(value: number) {
  return Math.round(value * 1000) / 1000
}

/** Convert floorplan whitebox JSON into spatial-reasoning SceneResponse. */
export function normalizedSceneToSceneResponse(
  normalized: NormalizedScene,
  extras?: {
    objects?: SceneObject[]
    suggestions?: SceneResponse["suggestions"]
  },
): SceneResponse {
  const extents = polygonExtents(normalized.floorPolygon)
  const wallHeight = normalized.wallHeight ?? 3
  const openings = (normalized.wallFixtures ?? [])
    .map((fixture) => fixtureToOpening(fixture, normalized.walls, wallHeight))
    .filter((item): item is SceneOpening => Boolean(item))

  return {
    sceneId: normalized.sceneId,
    unit: normalized.unit || "meter",
    room: {
      width: round3(extents.width),
      depth: round3(extents.depth),
      height: wallHeight,
    },
    objects: extras?.objects ?? [],
    openings,
    suggestions: extras?.suggestions ?? [],
  }
}

export function upsertSceneObject(
  scene: SceneResponse,
  object: SceneObject,
): SceneResponse {
  const others = scene.objects.filter((item) => item.id !== object.id)
  return { ...scene, objects: [...others, object] }
}
