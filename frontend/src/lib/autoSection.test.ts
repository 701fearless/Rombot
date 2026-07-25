import { describe, expect, it } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import * as THREE from "three"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"

import {
  AUTO_SECTION_RAY_SAMPLES,
  AUTO_SECTION_MIN_POLAR_ANGLE,
  createWallSectionIndex,
  selectFrontmostSectionWall,
  selectSectionWall,
  wallIdFromObject,
  type SectionRayHit,
  type WallSectionGroup,
} from "./autoSection"

function group(normal: THREE.Vector2): Pick<WallSectionGroup, "normal"> {
  return { normal }
}

function hits(wallId: string, count: number, distance = 3): SectionRayHit[] {
  return Array.from({ length: count }, () => ({ wallId, distance }))
}

async function loadCompetitionWhitebox(): Promise<THREE.Group> {
  const bytes = readFileSync(
    path.resolve(process.cwd(), "../backend/sample_data/floorplans/preprocessed/room6/whitebox.glb"),
  )
  const arrayBuffer = bytes.buffer.slice(
    bytes.byteOffset,
    bytes.byteOffset + bytes.byteLength,
  ) as ArrayBuffer
  return new Promise((resolve, reject) => {
    new GLTFLoader().parse(arrayBuffer, "", (gltf) => resolve(gltf.scene), reject)
  })
}

describe("wall section grouping", () => {
  it("groups split wall blocks and spatially attaches fixtures", () => {
    const root = new THREE.Group()
    const first = new THREE.Mesh(new THREE.BoxGeometry(3, 3, 0.1))
    first.name = "wall_001_block_01_01"
    first.position.x = -1.5
    const second = new THREE.Mesh(new THREE.BoxGeometry(3, 3, 0.1))
    second.name = "wall_001_block_02_01"
    second.position.x = 1.5
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.9, 2.1, 0.04))
    door.name = "door_entry_panel"
    door.position.set(0, -0.45, 0.04)
    root.add(first, second, door)

    const index = createWallSectionIndex(root)
    expect(index.groups.size).toBe(1)
    expect(index.groups.get("wall_001")?.wallMeshes).toHaveLength(2)
    expect(index.groups.get("wall_001")?.fixtureMeshes).toContain(door)
  })

  it("prefers explicit GLB extras over the node name", () => {
    const wall = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 0.1))
    wall.name = "generated_mesh"
    wall.userData = { rombotKind: "wall", wallId: "wall_metadata" }
    expect(wallIdFromObject(wall)).toBe("wall_metadata")
  })
})

describe("selectSectionWall", () => {
  const polarAngle = THREE.MathUtils.degToRad(60)
  const cameraTargetDistance = 8

  it("accepts 74 degrees and rejects 76 degrees from the wall normal", () => {
    const groups = new Map([["wall_a", group(new THREE.Vector2(1, 0))]])
    const accepted = selectSectionWall({
      hits: hits("wall_a", 4),
      groups,
      viewDirectionXZ: new THREE.Vector2(
        Math.cos(THREE.MathUtils.degToRad(74)),
        Math.sin(THREE.MathUtils.degToRad(74)),
      ),
      polarAngle,
      cameraTargetDistance,
      currentWallId: null,
    })
    const rejected = selectSectionWall({
      hits: hits("wall_a", 4),
      groups,
      viewDirectionXZ: new THREE.Vector2(
        Math.cos(THREE.MathUtils.degToRad(76)),
        Math.sin(THREE.MathUtils.degToRad(76)),
      ),
      polarAngle,
      cameraTargetDistance,
      currentWallId: null,
    })
    expect(accepted?.wallId).toBe("wall_a")
    expect(rejected).toBeNull()
  })

  it("restores every wall for a top-down view", () => {
    const selected = selectSectionWall({
      hits: hits("wall_a", 9),
      groups: new Map([["wall_a", group(new THREE.Vector2(1, 0))]]),
      viewDirectionXZ: new THREE.Vector2(1, 0),
      polarAngle: AUTO_SECTION_MIN_POLAR_ANGLE - 0.01,
      cameraTargetDistance,
      currentWallId: "wall_a",
    })
    expect(selected).toBeNull()
  })

  it("keeps the current wall until a challenger exceeds the switch margin", () => {
    const groups = new Map([
      ["wall_a", group(new THREE.Vector2(1, 0))],
      ["wall_b", group(new THREE.Vector2(1, 0))],
    ])
    const stable = selectSectionWall({
      hits: [...hits("wall_a", 4), ...hits("wall_b", 5)],
      groups,
      viewDirectionXZ: new THREE.Vector2(1, 0),
      polarAngle,
      cameraTargetDistance,
      currentWallId: "wall_a",
    })
    const switched = selectSectionWall({
      hits: [...hits("wall_a", 2, 4), ...hits("wall_b", 7, 2)],
      groups,
      viewDirectionXZ: new THREE.Vector2(1, 0),
      polarAngle,
      cameraTargetDistance,
      currentWallId: "wall_a",
    })
    expect(stable?.wallId).toBe("wall_a")
    expect(switched?.wallId).toBe("wall_b")
  })

  it("requires at least two first-hit rays", () => {
    const selected = selectSectionWall({
      hits: hits("wall_a", 1),
      groups: new Map([["wall_a", group(new THREE.Vector2(1, 0))]]),
      viewDirectionXZ: new THREE.Vector2(1, 0),
      polarAngle,
      cameraTargetDistance,
      currentWallId: null,
    })
    expect(selected).toBeNull()
  })
})

describe("competition whitebox compatibility", () => {
  it("selects one section wall from four desktop orbit directions", async () => {
    const root = await loadCompetitionWhitebox()
    const initialBounds = new THREE.Box3().setFromObject(root)
    const size = initialBounds.getSize(new THREE.Vector3())
    root.position.sub(initialBounds.getCenter(new THREE.Vector3()))
    root.updateMatrixWorld(true)
    const index = createWallSectionIndex(root)
    console.log('ROOM6_WALL_GROUPS', JSON.stringify([...index.groups.values()].map((item) => ({ id: item.id, normal: item.normal.toArray().map((value) => Number(value.toFixed(3))), planeOffset: Number(item.planeOffset.toFixed(3)), minAlong: Number(item.minAlong.toFixed(3)), maxAlong: Number(item.maxAlong.toFixed(3)), meshes: item.wallMeshes.length }))))
    const radius = Math.max(size.x, size.y, size.z, 1)
    const camera = new THREE.PerspectiveCamera(42, 680 / 520, 0.01, radius * 100)
    const raycaster = new THREE.Raycaster()
    const selectedWalls = new Set<string>()
    let currentWallId: string | null = null

    for (const [x, z] of [
      [1.15, 1.15],
      [-1.15, 1.15],
      [-1.15, -1.15],
      [1.15, -1.15],
    ]) {
      camera.position.set(x * radius, 0.95 * radius, z * radius)
      camera.lookAt(0, 0, 0)
      camera.updateMatrixWorld(true)
      const targetDistance = camera.position.length()
      const rayHits: SectionRayHit[] = []
      for (const sample of AUTO_SECTION_RAY_SAMPLES) {
        raycaster.setFromCamera(sample, camera)
        const intersection = raycaster
          .intersectObjects(index.wallMeshes, false)
          .find((item) => item.distance <= targetDistance * 1.05)
        if (!intersection) continue
        const wallId = index.meshToWallId.get(intersection.object)
        if (wallId) rayHits.push({ wallId, distance: intersection.distance })
      }
      const selected = selectSectionWall({
        hits: rayHits,
        groups: index.groups,
        viewDirectionXZ: new THREE.Vector2(-camera.position.x, -camera.position.z),
        polarAngle: Math.acos(camera.position.y / targetDistance),
        cameraTargetDistance: targetDistance,
        currentWallId,
      })
      expect(selected).not.toBeNull()
      currentWallId = selected?.wallId ?? null
      if (currentWallId) selectedWalls.add(currentWallId)
    }

    expect(index.groups.size).toBe(18)
    expect(selectedWalls.size).toBeGreaterThanOrEqual(3)
    expect(
      [...index.groups.values()].reduce(
        (count, group) => count + group.fixtureMeshes.length,
        0,
      ),
    ).toBeGreaterThan(0)
  })

  it("selects a front wall throughout a full desktop orbit", async () => {
    const root = await loadCompetitionWhitebox()
    const initialBounds = new THREE.Box3().setFromObject(root)
    const size = initialBounds.getSize(new THREE.Vector3())
    root.position.sub(initialBounds.getCenter(new THREE.Vector3()))
    root.updateMatrixWorld(true)
    const index = createWallSectionIndex(root)
    const radius = Math.max(size.x, size.y, size.z, 1)
    const camera = new THREE.PerspectiveCamera(42, 680 / 520, 0.01, radius * 100)
    const raycaster = new THREE.Raycaster()
    const selectedWalls = new Set<string>()
    let currentWallId: string | null = null

    for (let step = 0; step < 24; step += 1) {
      const angle = step / 24 * Math.PI * 2
      camera.position.set(
        Math.cos(angle) * radius * 1.55,
        radius * .95,
        Math.sin(angle) * radius * 1.55,
      )
      camera.lookAt(0, 0, 0)
      camera.updateMatrixWorld(true)
      const targetDistance = camera.position.length()
      const rayHits: SectionRayHit[] = []
      for (const sample of AUTO_SECTION_RAY_SAMPLES) {
        raycaster.setFromCamera(sample, camera)
        const intersection = raycaster.intersectObjects(index.wallMeshes, false)[0]
        if (!intersection) continue
        const wallId = index.meshToWallId.get(intersection.object)
        if (wallId) rayHits.push({ wallId, distance: intersection.distance })
      }
      const selected = selectFrontmostSectionWall({
        hits: rayHits,
        groups: index.groups,
        viewDirectionXZ: new THREE.Vector2(-camera.position.x, -camera.position.z),
        polarAngle: Math.acos(camera.position.y / targetDistance),
        cameraTargetDistance: targetDistance,
        currentWallId,
      })
      expect(selected, `orbit step ${step}`).not.toBeNull()
      currentWallId = selected?.wallId ?? null
      if (currentWallId) selectedWalls.add(currentWallId)
    }

    expect(selectedWalls.size).toBeGreaterThanOrEqual(4)
  })
})
