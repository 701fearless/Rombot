import { useEffect, useRef, useState } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"

import { apiUrl } from "../lib/api"
import {
  AUTO_SECTION_FADE_MS,
  AUTO_SECTION_RAY_SAMPLES,
  createWallSectionIndex,
  selectSectionWall,
  type WallSectionGroup,
  type WallSectionIndex,
} from "../lib/autoSection"
import type { PrebuiltAsset } from "../types"

interface FloorplanViewerProps {
  modelUrl: string
  furniture?: PrebuiltAsset | null
  autoSection?: boolean
}

interface FurnitureTransform {
  x: number
  z: number
  rotation: number
  scale: number
}

type ViewerStatus = "loading" | "ready" | "error"

interface DisposalTracker {
  geometries: Set<THREE.BufferGeometry>
  materials: Set<THREE.Material>
  textures: Set<THREE.Texture>
}

interface FadeMaterial {
  material: THREE.Material
  baseOpacity: number
  baseTransparent: boolean
  baseDepthWrite: boolean
}

interface FadeWall {
  materials: FadeMaterial[]
  current: number
  target: number
}

const INITIAL_TRANSFORM: FurnitureTransform = {
  x: 0,
  z: 0,
  rotation: 0,
  scale: 1,
}

function createDisposalTracker(): DisposalTracker {
  return {
    geometries: new Set(),
    materials: new Set(),
    textures: new Set(),
  }
}

function disposeMaterial(material: THREE.Material, tracker: DisposalTracker) {
  if (tracker.materials.has(material)) return
  tracker.materials.add(material)
  const record = material as unknown as Record<string, unknown>
  Object.values(record).forEach((value) => {
    if (value instanceof THREE.Texture && !tracker.textures.has(value)) {
      tracker.textures.add(value)
      value.dispose()
    }
  })
  material.dispose()
}

function disposeObject(object: THREE.Object3D, tracker: DisposalTracker) {
  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return
    if (!tracker.geometries.has(child.geometry)) {
      tracker.geometries.add(child.geometry)
      child.geometry.dispose()
    }
    const materials = Array.isArray(child.material) ? child.material : [child.material]
    materials.forEach((material) => disposeMaterial(material, tracker))
  })
}

function prepareFadeWall(
  group: WallSectionGroup,
  orphanedMaterials: Set<THREE.Material>,
): FadeWall {
  const fadeMaterials: FadeMaterial[] = []
  const meshes = new Set([...group.wallMeshes, ...group.fixtureMeshes])
  for (const mesh of meshes) {
    const source = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
    source.forEach((material) => orphanedMaterials.add(material))
    const clones = source.map((material) => {
      const clone = material.clone()
      fadeMaterials.push({
        material: clone,
        baseOpacity: clone.opacity,
        baseTransparent: clone.transparent,
        baseDepthWrite: clone.depthWrite,
      })
      return clone
    })
    mesh.material = Array.isArray(mesh.material) ? clones : clones[0]
  }
  return { materials: fadeMaterials, current: 1, target: 1 }
}

function animateFadeWall(wall: FadeWall, deltaMs: number) {
  const previous = wall.current
  const step = deltaMs / AUTO_SECTION_FADE_MS
  wall.current =
    wall.target < wall.current
      ? Math.max(wall.target, wall.current - step)
      : Math.min(wall.target, wall.current + step)
  if (Math.abs(previous - wall.current) < 1e-6) return

  const fullyVisible = wall.current >= 0.999
  for (const state of wall.materials) {
    const transparent = !fullyVisible || state.baseTransparent
    if (state.material.transparent !== transparent) {
      state.material.transparent = transparent
      state.material.needsUpdate = true
    }
    state.material.opacity = state.baseOpacity * wall.current
    state.material.depthWrite = fullyVisible ? state.baseDepthWrite : false
  }
}

export function FloorplanViewer({
  modelUrl,
  furniture,
  autoSection = true,
}: FloorplanViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const applyTransformRef = useRef<((value: FurnitureTransform) => void) | null>(null)
  const movementBoundsRef = useRef({ x: 0, z: 0 })
  const [status, setStatus] = useState<ViewerStatus>("loading")
  const [message, setMessage] = useState("正在加载户型白模")
  const [furnitureReady, setFurnitureReady] = useState(false)
  const [transform, setTransform] = useState<FurnitureTransform>(INITIAL_TRANSFORM)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let disposed = false
    let frameId = 0
    let floorModel: THREE.Object3D | null = null
    let furnitureModel: THREE.Object3D | null = null
    let grid: THREE.GridHelper | null = null
    let renderer: THREE.WebGLRenderer
    let floorBounds: THREE.Box3 | null = null
    let furnitureBaseScale = new THREE.Vector3(1, 1, 1)
    let sectionIndex: WallSectionIndex | null = null
    let hiddenWallId: string | null = null
    let sectionDirty = true
    const fadeWalls = new Map<string, FadeWall>()
    const orphanedMaterials = new Set<THREE.Material>()
    const raycaster = new THREE.Raycaster()
    const renderClock = new THREE.Clock()

    setStatus("loading")
    setMessage("正在加载户型白模")
    setFurnitureReady(false)
    setTransform(INITIAL_TRANSFORM)

    const scene = new THREE.Scene()
    scene.background = new THREE.Color("#11140f")
    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 2000)

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    } catch {
      setStatus("error")
      setMessage("当前浏览器无法创建 3D 预览")
      return
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.05
    renderer.domElement.setAttribute("aria-label", "户型与家具组合预览")
    renderer.domElement.setAttribute("role", "img")
    container.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.minPolarAngle = 0.18
    controls.maxPolarAngle = Math.PI / 2.02
    const markSectionDirty = () => {
      sectionDirty = true
    }
    controls.addEventListener("change", markSectionDirty)

    scene.add(new THREE.HemisphereLight("#f5f1dd", "#36402d", 2.4))
    const keyLight = new THREE.DirectionalLight("#ffffff", 3.2)
    keyLight.position.set(7, 12, 8)
    scene.add(keyLight)
    const fillLight = new THREE.DirectionalLight("#d7ff67", 1.2)
    fillLight.position.set(-8, 5, -4)
    scene.add(fillLight)

    const resize = () => {
      const width = Math.max(container.clientWidth, 1)
      const height = Math.max(container.clientHeight, 1)
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      sectionDirty = true
    }
    resize()
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container)

    const evaluateAutoSection = () => {
      if (!autoSection || !sectionIndex) return
      camera.updateMatrixWorld(true)
      const targetDistance = camera.position.distanceTo(controls.target)
      const hits = []
      for (const sample of AUTO_SECTION_RAY_SAMPLES) {
        raycaster.setFromCamera(sample, camera)
        const intersection = raycaster
          .intersectObjects(sectionIndex.wallMeshes, false)
          .find((item) => item.distance <= targetDistance * 1.05)
        if (!intersection) continue
        const wallId = sectionIndex.meshToWallId.get(intersection.object)
        if (wallId) hits.push({ wallId, distance: intersection.distance })
      }

      const candidate = selectSectionWall({
        hits,
        groups: sectionIndex.groups,
        viewDirectionXZ: new THREE.Vector2(
          controls.target.x - camera.position.x,
          controls.target.z - camera.position.z,
        ),
        polarAngle: controls.getPolarAngle(),
        cameraTargetDistance: targetDistance,
        currentWallId: hiddenWallId,
      })
      hiddenWallId = candidate?.wallId ?? null
      container.dataset.sectionWall = hiddenWallId ?? ""
      fadeWalls.forEach((wall, wallId) => {
        wall.target = wallId === hiddenWallId ? 0 : 1
      })
    }

    const placeFurniture = (value: FurnitureTransform) => {
      if (!furnitureModel || !floorBounds) return
      furnitureModel.scale.set(
        furnitureBaseScale.x * value.scale,
        furnitureBaseScale.y * value.scale,
        furnitureBaseScale.z * value.scale,
      )
      furnitureModel.rotation.set(0, value.rotation, 0)
      furnitureModel.position.set(value.x, 0, value.z)
      const bounds = new THREE.Box3().setFromObject(furnitureModel)
      furnitureModel.position.y += floorBounds.min.y - bounds.min.y + 0.035
    }
    applyTransformRef.current = placeFurniture

    const loadFurniture = () => {
      if (!furniture || !floorBounds) {
        setStatus("ready")
        setMessage("拖动旋转 · 双指或滚轮缩放")
        return
      }
      setMessage("正在把家具放进户型")
      new GLTFLoader().load(
        apiUrl(furniture.glbUrl),
        (gltf) => {
          if (disposed) return
          furnitureModel = gltf.scene
          const rawBounds = new THREE.Box3().setFromObject(furnitureModel)
          const rawSize = rawBounds.getSize(new THREE.Vector3())
          const dimensions = furniture.estimatedDimensions
          if (dimensions && rawSize.x > 0 && rawSize.y > 0 && rawSize.z > 0) {
            furnitureBaseScale = new THREE.Vector3(
              dimensions.widthM / rawSize.x,
              dimensions.heightM / rawSize.y,
              dimensions.depthM / rawSize.z,
            )
          } else {
            const floorSize = floorBounds!.getSize(new THREE.Vector3())
            const target = Math.max(Math.min(floorSize.x, floorSize.z) * 0.2, 0.5)
            const uniform = target / Math.max(rawSize.x, rawSize.y, rawSize.z, 0.001)
            furnitureBaseScale.setScalar(uniform)
          }
          scene.add(furnitureModel)
          placeFurniture(INITIAL_TRANSFORM)
          setFurnitureReady(true)
          setStatus("ready")
          setMessage(`${furniture.name || furniture.label}已放入户型`)
        },
        undefined,
        () => {
          if (disposed) return
          setStatus("error")
          setMessage("家具模型加载失败，请重新选择")
        },
      )
    }

    new GLTFLoader().load(
      apiUrl(modelUrl),
      (gltf) => {
        if (disposed) return
        floorModel = gltf.scene
        const initialBounds = new THREE.Box3().setFromObject(floorModel)
        const size = initialBounds.getSize(new THREE.Vector3())
        const center = initialBounds.getCenter(new THREE.Vector3())
        floorModel.position.sub(center)
        scene.add(floorModel)
        floorModel.updateMatrixWorld(true)
        if (autoSection) {
          sectionIndex = createWallSectionIndex(floorModel)
          sectionIndex.groups.forEach((group, wallId) => {
            fadeWalls.set(wallId, prepareFadeWall(group, orphanedMaterials))
          })
          sectionDirty = true
        }
        floorBounds = new THREE.Box3().setFromObject(floorModel)
        movementBoundsRef.current = {
          x: Math.max(size.x / 2 - 0.25, 0),
          z: Math.max(size.z / 2 - 0.25, 0),
        }

        const radius = Math.max(size.x, size.y, size.z, 1)
        camera.near = Math.max(radius / 1000, 0.01)
        camera.far = radius * 100
        camera.position.set(radius * 1.15, radius * 0.95, radius * 1.15)
        camera.updateProjectionMatrix()
        controls.target.set(0, 0, 0)
        controls.minDistance = radius * 0.25
        controls.maxDistance = radius * 5
        controls.update()

        grid = new THREE.GridHelper(radius * 2.6, 16, "#6f7e52", "#293025")
        grid.position.y = floorBounds.min.y - 0.01
        scene.add(grid)
        loadFurniture()
      },
      undefined,
      () => {
        if (disposed) return
        setStatus("error")
        setMessage("户型白模加载失败")
      },
    )

    const render = () => {
      if (disposed) return
      controls.update()
      if (sectionDirty) {
        sectionDirty = false
        evaluateAutoSection()
      }
      const deltaMs = Math.min(renderClock.getDelta() * 1000, 50)
      fadeWalls.forEach((wall) => animateFadeWall(wall, deltaMs))
      renderer.render(scene, camera)
      frameId = window.requestAnimationFrame(render)
    }
    render()

    return () => {
      disposed = true
      applyTransformRef.current = null
      delete container.dataset.sectionWall
      window.cancelAnimationFrame(frameId)
      resizeObserver.disconnect()
      controls.removeEventListener("change", markSectionDirty)
      controls.dispose()
      const tracker = createDisposalTracker()
      if (floorModel) disposeObject(floorModel, tracker)
      if (furnitureModel) disposeObject(furnitureModel, tracker)
      orphanedMaterials.forEach((material) => disposeMaterial(material, tracker))
      if (grid) {
        if (!tracker.geometries.has(grid.geometry)) {
          tracker.geometries.add(grid.geometry)
          grid.geometry.dispose()
        }
        const materials = Array.isArray(grid.material) ? grid.material : [grid.material]
        materials.forEach((material) => disposeMaterial(material, tracker))
      }
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [autoSection, furniture, modelUrl])

  const updateFurniture = (
    updater: (current: FurnitureTransform) => FurnitureTransform,
  ) => {
    setTransform((current) => {
      const proposed = updater(current)
      const bounds = movementBoundsRef.current
      const next = {
        ...proposed,
        x: Math.max(-bounds.x, Math.min(bounds.x, proposed.x)),
        z: Math.max(-bounds.z, Math.min(bounds.z, proposed.z)),
        scale: Math.max(0.5, Math.min(1.5, proposed.scale)),
      }
      applyTransformRef.current?.(next)
      return next
    })
  }

  return (
    <div className="floorplan-viewer" data-status={status}>
      <div ref={containerRef} className="floorplan-viewer__canvas" />
      <div className="floorplan-viewer__status" role="status">
        <span className={status === "loading" ? "viewer-spinner" : ""} />
        {message}
      </div>

      {furniture && furnitureReady && (
        <div className="furniture-controls" aria-label="调整家具">
          <div>
            <button
              type="button"
              onClick={() => updateFurniture((value) => ({ ...value, z: value.z - 0.2 }))}
              aria-label="家具向前"
            >
              ↑
            </button>
            <button
              type="button"
              onClick={() => updateFurniture((value) => ({ ...value, x: value.x - 0.2 }))}
              aria-label="家具向左"
            >
              ←
            </button>
            <button
              type="button"
              onClick={() => updateFurniture((value) => ({ ...value, x: value.x + 0.2 }))}
              aria-label="家具向右"
            >
              →
            </button>
            <button
              type="button"
              onClick={() => updateFurniture((value) => ({ ...value, z: value.z + 0.2 }))}
              aria-label="家具向后"
            >
              ↓
            </button>
          </div>
          <div>
            <button
              type="button"
              onClick={() =>
                updateFurniture((value) => ({
                  ...value,
                  rotation: value.rotation - Math.PI / 12,
                }))
              }
              aria-label="家具向左旋转"
            >
              ↶
            </button>
            <button
              type="button"
              onClick={() =>
                updateFurniture((value) => ({
                  ...value,
                  rotation: value.rotation + Math.PI / 12,
                }))
              }
              aria-label="家具向右旋转"
            >
              ↷
            </button>
            <button
              type="button"
              onClick={() =>
                updateFurniture((value) => ({ ...value, scale: value.scale - 0.1 }))
              }
              aria-label="缩小家具"
            >
              −
            </button>
            <button
              type="button"
              onClick={() =>
                updateFurniture((value) => ({ ...value, scale: value.scale + 0.1 }))
              }
              aria-label="放大家具"
            >
              ＋
            </button>
            <button
              type="button"
              onClick={() => updateFurniture(() => INITIAL_TRANSFORM)}
            >
              重置
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
