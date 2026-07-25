import * as THREE from "three"

export const AUTO_SECTION_CONE_DEGREES = 150
export const AUTO_SECTION_HALF_ANGLE_DEGREES = AUTO_SECTION_CONE_DEGREES / 2
export const AUTO_SECTION_MIN_POLAR_ANGLE = THREE.MathUtils.degToRad(35)
export const AUTO_SECTION_SWITCH_MARGIN = 0.12
export const AUTO_SECTION_FADE_MS = 180
export const AUTO_SECTION_FIXTURE_DISTANCE_M = 0.25

export const AUTO_SECTION_RAY_SAMPLES = [
  new THREE.Vector2(-0.22, -0.15),
  new THREE.Vector2(0, -0.15),
  new THREE.Vector2(0.22, -0.15),
  new THREE.Vector2(-0.22, 0),
  new THREE.Vector2(0, 0),
  new THREE.Vector2(0.22, 0),
  new THREE.Vector2(-0.22, 0.15),
  new THREE.Vector2(0, 0.15),
  new THREE.Vector2(0.22, 0.15),
] as const

export interface WallSectionGroup {
  id: string
  wallMeshes: THREE.Mesh[]
  fixtureMeshes: THREE.Mesh[]
  tangent: THREE.Vector2
  normal: THREE.Vector2
  planeOffset: number
  minAlong: number
  maxAlong: number
}

export interface WallSectionIndex {
  groups: Map<string, WallSectionGroup>
  wallMeshes: THREE.Mesh[]
  meshToWallId: Map<THREE.Object3D, string>
}

export interface SectionRayHit {
  wallId: string
  distance: number
}

export interface SectionWallCandidate {
  wallId: string
  score: number
  coverage: number
  incidence: number
  proximity: number
}

interface SelectSectionWallInput {
  hits: SectionRayHit[]
  groups: Map<string, Pick<WallSectionGroup, "normal">>
  viewDirectionXZ: THREE.Vector2
  polarAngle: number
  cameraTargetDistance: number
  currentWallId: string | null
}

function inheritedUserData(
  object: THREE.Object3D,
  key: string,
): unknown {
  let current: THREE.Object3D | null = object
  while (current) {
    if (current.userData[key] !== undefined) return current.userData[key]
    current = current.parent
  }
  return undefined
}

export function wallIdFromObject(object: THREE.Object3D): string | null {
  const kind = inheritedUserData(object, "rombotKind")
  const metadataWallId = inheritedUserData(object, "wallId")
  if (kind === "wall" && typeof metadataWallId === "string") {
    return metadataWallId
  }
  const name = object.name.trim()
  if (!name.startsWith("wall_")) return null
  return name.replace(/_block_\d+_\d+$/, "")
}

function fixtureWallIdFromObject(object: THREE.Object3D): string | null {
  const kind = inheritedUserData(object, "rombotKind")
  const metadataWallId = inheritedUserData(object, "wallId")
  return kind === "fixture" && typeof metadataWallId === "string"
    ? metadataWallId
    : null
}

function isFixtureObject(object: THREE.Object3D): boolean {
  if (inheritedUserData(object, "rombotKind") === "fixture") return true
  return /^(door|window)_/i.test(object.name)
}

function collectWorldXZ(meshes: THREE.Mesh[]): THREE.Vector2[] {
  const points: THREE.Vector2[] = []
  const point = new THREE.Vector3()
  for (const mesh of meshes) {
    const position = mesh.geometry.getAttribute("position")
    if (!position) continue
    for (let index = 0; index < position.count; index += 1) {
      point.fromBufferAttribute(position, index).applyMatrix4(mesh.matrixWorld)
      points.push(new THREE.Vector2(point.x, point.z))
    }
  }
  return points
}

function analyzeWallGeometry(group: WallSectionGroup) {
  const points = collectWorldXZ(group.wallMeshes)
  if (!points.length) return

  const center = points
    .reduce((sum, point) => sum.add(point), new THREE.Vector2())
    .multiplyScalar(1 / points.length)
  let xx = 0
  let xz = 0
  let zz = 0
  for (const point of points) {
    const x = point.x - center.x
    const z = point.y - center.y
    xx += x * x
    xz += x * z
    zz += z * z
  }
  const angle = 0.5 * Math.atan2(2 * xz, xx - zz)
  group.tangent.set(Math.cos(angle), Math.sin(angle)).normalize()
  group.normal.set(-group.tangent.y, group.tangent.x)
  group.planeOffset =
    points.reduce((sum, point) => sum + point.dot(group.normal), 0) / points.length

  const along = points.map((point) => point.dot(group.tangent))
  group.minAlong = Math.min(...along)
  group.maxAlong = Math.max(...along)
}

function fixtureCenter(mesh: THREE.Mesh): THREE.Vector2 {
  const center = new THREE.Box3()
    .setFromObject(mesh)
    .getCenter(new THREE.Vector3())
  return new THREE.Vector2(center.x, center.z)
}

function findFixtureWall(
  mesh: THREE.Mesh,
  groups: Map<string, WallSectionGroup>,
): WallSectionGroup | null {
  const center = fixtureCenter(mesh)
  let best: WallSectionGroup | null = null
  let bestDistance = Number.POSITIVE_INFINITY
  for (const group of groups.values()) {
    const normalDistance = Math.abs(center.dot(group.normal) - group.planeOffset)
    const along = center.dot(group.tangent)
    const insideWallSpan =
      along >= group.minAlong - 0.15 && along <= group.maxAlong + 0.15
    if (
      insideWallSpan &&
      normalDistance <= AUTO_SECTION_FIXTURE_DISTANCE_M &&
      normalDistance < bestDistance
    ) {
      best = group
      bestDistance = normalDistance
    }
  }
  return best
}

export function createWallSectionIndex(root: THREE.Object3D): WallSectionIndex {
  root.updateMatrixWorld(true)
  const groups = new Map<string, WallSectionGroup>()
  const wallMeshes: THREE.Mesh[] = []
  const fixtureMeshes: THREE.Mesh[] = []
  const meshToWallId = new Map<THREE.Object3D, string>()

  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return
    const wallId = wallIdFromObject(object)
    if (wallId) {
      let group = groups.get(wallId)
      if (!group) {
        group = {
          id: wallId,
          wallMeshes: [],
          fixtureMeshes: [],
          tangent: new THREE.Vector2(1, 0),
          normal: new THREE.Vector2(0, 1),
          planeOffset: 0,
          minAlong: 0,
          maxAlong: 0,
        }
        groups.set(wallId, group)
      }
      group.wallMeshes.push(object)
      wallMeshes.push(object)
      meshToWallId.set(object, wallId)
    } else if (isFixtureObject(object)) {
      fixtureMeshes.push(object)
    }
  })

  groups.forEach(analyzeWallGeometry)

  for (const fixture of fixtureMeshes) {
    const metadataWallId = fixtureWallIdFromObject(fixture)
    const group =
      (metadataWallId ? groups.get(metadataWallId) : null) ??
      findFixtureWall(fixture, groups)
    if (!group) continue
    group.fixtureMeshes.push(fixture)
  }

  return { groups, wallMeshes, meshToWallId }
}

function clamp01(value: number) {
  return Math.max(0, Math.min(1, value))
}

export function selectSectionWall({
  hits,
  groups,
  viewDirectionXZ,
  polarAngle,
  cameraTargetDistance,
  currentWallId,
}: SelectSectionWallInput): SectionWallCandidate | null {
  if (
    polarAngle < AUTO_SECTION_MIN_POLAR_ANGLE ||
    viewDirectionXZ.lengthSq() < 1e-8
  ) {
    return null
  }

  const view = viewDirectionXZ.clone().normalize()
  const hitStats = new Map<string, { count: number; nearest: number }>()
  for (const hit of hits) {
    const stats = hitStats.get(hit.wallId) ?? {
      count: 0,
      nearest: Number.POSITIVE_INFINITY,
    }
    stats.count += 1
    stats.nearest = Math.min(stats.nearest, hit.distance)
    hitStats.set(hit.wallId, stats)
  }

  const minimumIncidence = Math.cos(
    THREE.MathUtils.degToRad(AUTO_SECTION_HALF_ANGLE_DEGREES),
  )
  const candidates: SectionWallCandidate[] = []
  for (const [wallId, stats] of hitStats) {
    if (stats.count < 2) continue
    const group = groups.get(wallId)
    if (!group) continue
    const incidence = Math.abs(view.dot(group.normal))
    if (incidence < minimumIncidence) continue
    const coverage = stats.count / AUTO_SECTION_RAY_SAMPLES.length
    const proximity = clamp01(
      1 - stats.nearest / Math.max(cameraTargetDistance * 1.5, 0.001),
    )
    candidates.push({
      wallId,
      coverage,
      incidence,
      proximity,
      score: coverage * 0.65 + incidence * 0.25 + proximity * 0.1,
    })
  }

  candidates.sort(
    (left, right) =>
      right.score - left.score ||
      right.coverage - left.coverage ||
      left.wallId.localeCompare(right.wallId),
  )
  const best = candidates[0]
  if (!best) return null

  const current = currentWallId
    ? candidates.find((candidate) => candidate.wallId === currentWallId)
    : null
  if (
    current &&
    current.wallId !== best.wallId &&
    best.score < current.score + AUTO_SECTION_SWITCH_MARGIN
  ) {
    return current
  }
  return best
}
