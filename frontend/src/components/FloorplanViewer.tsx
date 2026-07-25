import { useEffect, useRef, useState } from "react"
import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js"
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js"

import { apiUrl, saveFloorplanWhitebox } from "../lib/api"
import {
  AUTO_SECTION_FADE_MS,
  AUTO_SECTION_RAY_SAMPLES,
  createWallSectionIndex,
  selectSectionWall,
  type WallSectionGroup,
  type WallSectionIndex,
} from "../lib/autoSection"
import { layoutToViewer, viewerToLayout } from "../lib/sceneCoords"
import { inferWallLockAxis, snapWallPosition } from "../lib/wallSnap"
import type {
  FurnitureLayoutPose,
  FurnitureTransformChange,
  PrebuiltAsset,
} from "../types"

export type SandboxMode = "furniture" | "walls"

interface FloorplanViewerProps {
  modelUrl: string
  furniture?: PrebuiltAsset | null
  autoSection?: boolean
  sceneId?: string
  roomWidth?: number
  roomDepth?: number
  layoutPose?: FurnitureLayoutPose | null
  suggestionPose?: FurnitureLayoutPose | null
  onTransformChange?: (change: FurnitureTransformChange) => void
  defaultMode?: SandboxMode
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

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
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

function findEditableWall(object: THREE.Object3D | null): THREE.Object3D | null {
  let current = object
  while (current) {
    if (current.userData.rombotKind === "editableWall") return current
    current = current.parent
  }
  return null
}

function downloadArrayBuffer(buffer: ArrayBuffer, filename: string) {
  const blob = new Blob([buffer], { type: "model/gltf-binary" })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function FloorplanViewer({
  modelUrl,
  furniture,
  autoSection = true,
  sceneId,
  roomWidth = 6,
  roomDepth = 4.2,
  layoutPose = null,
  suggestionPose = null,
  onTransformChange,
  defaultMode = "furniture",
}: FloorplanViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const applyTransformRef = useRef<((value: FurnitureTransform) => void) | null>(null)
  const movementBoundsRef = useRef({ x: 0, z: 0 })
  const transformRef = useRef<FurnitureTransform>(INITIAL_TRANSFORM)
  const modeRef = useRef<SandboxMode>(defaultMode)
  const exportHouseRef = useRef<(() => Promise<ArrayBuffer>) | null>(null)
  const deleteSelectedWallRef = useRef<(() => boolean) | null>(null)
  const selectedWallIdRef = useRef<string | null>(null)
  const roomRef = useRef({ width: roomWidth, depth: roomDepth })
  const onTransformChangeRef = useRef(onTransformChange)
  const layoutPoseRef = useRef(layoutPose)
  const baseSizeRef = useRef<[number, number, number]>([1, 0.8, 1])
  const emitFurnitureChangeRef = useRef<
    ((reason: FurnitureTransformChange["reason"]) => void) | null
  >(null)
  const applySuggestionPoseRef = useRef<((pose: FurnitureLayoutPose | null) => void) | null>(
    null,
  )

  const [status, setStatus] = useState<ViewerStatus>("loading")
  const [message, setMessage] = useState("正在加载户型白模")
  const [furnitureReady, setFurnitureReady] = useState(false)
  const [mode, setMode] = useState<SandboxMode>(defaultMode)
  const [selectedWallId, setSelectedWallId] = useState<string | null>(null)
  const [wallCount, setWallCount] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [busyAction, setBusyAction] = useState<"export" | "save" | null>(null)
  const [transform, setTransform] = useState<FurnitureTransform>(INITIAL_TRANSFORM)

  useEffect(() => {
    roomRef.current = { width: roomWidth, depth: roomDepth }
  }, [roomDepth, roomWidth])

  useEffect(() => {
    onTransformChangeRef.current = onTransformChange
  }, [onTransformChange])

  useEffect(() => {
    layoutPoseRef.current = layoutPose
  }, [layoutPose])

  useEffect(() => {
    transformRef.current = transform
  }, [transform])

  useEffect(() => {
    modeRef.current = mode
  }, [mode])

  useEffect(() => {
    selectedWallIdRef.current = selectedWallId
  }, [selectedWallId])

  useEffect(() => {
    if (furniture?.estimatedDimensions) {
      baseSizeRef.current = [
        furniture.estimatedDimensions.widthM,
        furniture.estimatedDimensions.heightM,
        furniture.estimatedDimensions.depthM,
      ]
    } else if (layoutPose?.size) {
      baseSizeRef.current = layoutPose.size
    }
  }, [furniture, layoutPose])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let disposed = false
    let frameId = 0
    let floorModel: THREE.Object3D | null = null
    let furnitureModel: THREE.Object3D | null = null
    let suggestionGhost: THREE.Mesh | null = null
    let selectionHelper: THREE.BoxHelper | null = null
    let grid: THREE.GridHelper | null = null
    let renderer: THREE.WebGLRenderer
    let floorBounds: THREE.Box3 | null = null
    let furnitureBaseScale = new THREE.Vector3(1, 1, 1)
    let lastDragKind: "furniture" | "wall" | null = null
    let sectionIndex: WallSectionIndex | null = null
    let hiddenWallId: string | null = null
    let sectionDirty = true
    let isDragging = false
    let dragKind: "furniture" | "wall" | null = null
    let activeWall: THREE.Object3D | null = null
    let wallLockAxis: "x" | "z" | null = null
    let wallLockValue = 0
    let snapGuideX: THREE.Line | null = null
    let snapGuideZ: THREE.Line | null = null
    const wallRoots = new Map<string, THREE.Group>()
    const fadeWalls = new Map<string, FadeWall>()
    const orphanedMaterials = new Set<THREE.Material>()
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
    const planeHit = new THREE.Vector3()
    const dragOffset = new THREE.Vector3()
    const renderClock = new THREE.Clock()

    setStatus("loading")
    setMessage("正在加载户型白模")
    setFurnitureReady(false)
    setSelectedWallId(null)
    setWallCount(0)
    setDragging(false)
    setTransform(INITIAL_TRANSFORM)
    transformRef.current = INITIAL_TRANSFORM

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
    renderer.domElement.setAttribute("aria-label", "可编辑户型沙盒")
    renderer.domElement.style.touchAction = "none"
    renderer.domElement.style.cursor = "grab"
    container.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.minPolarAngle = 0.08
    controls.maxPolarAngle = Math.PI / 2.15
    controls.enablePan = true
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

    const modeHint = () =>
      modeRef.current === "walls"
        ? "编辑墙体：拖动自动磁吸网格/墙线 · Delete 删除 · 空白处旋转"
        : furniture
          ? "摆放家具：点击拖动家具 · 空白处旋转视角"
          : "拖动旋转视角 · 滚轮缩放"

    const setPointerFromEvent = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      pointer.x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1
      pointer.y = -((event.clientY - rect.top) / Math.max(rect.height, 1)) * 2 + 1
    }

    const syncSelectionHelper = (target: THREE.Object3D | null) => {
      if (!selectionHelper) return
      if (!target) {
        selectionHelper.visible = false
        return
      }
      selectionHelper.setFromObject(target)
      selectionHelper.visible = true
    }

    const selectWall = (wall: THREE.Object3D | null) => {
      activeWall = wall
      const wallId = typeof wall?.userData.wallId === "string" ? wall.userData.wallId : null
      setSelectedWallId(wallId)
      selectedWallIdRef.current = wallId
      syncSelectionHelper(wall)
    }

    const clearSnapGuides = () => {
      if (snapGuideX) {
        snapGuideX.removeFromParent()
        snapGuideX.geometry.dispose()
        ;(snapGuideX.material as THREE.Material).dispose()
        snapGuideX = null
      }
      if (snapGuideZ) {
        snapGuideZ.removeFromParent()
        snapGuideZ.geometry.dispose()
        ;(snapGuideZ.material as THREE.Material).dispose()
        snapGuideZ = null
      }
    }

    const makeGuideLine = (
      axis: "x" | "z",
      value: number,
      halfSpan: number,
      y: number,
    ) => {
      const points =
        axis === "x"
          ? [new THREE.Vector3(value, y, -halfSpan), new THREE.Vector3(value, y, halfSpan)]
          : [new THREE.Vector3(-halfSpan, y, value), new THREE.Vector3(halfSpan, y, value)]
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({
        color: "#d7ff67",
        transparent: true,
        opacity: 0.85,
      })
      return new THREE.Line(geometry, material)
    }

    const updateSnapGuides = (guideX: number | null, guideZ: number | null) => {
      clearSnapGuides()
      if (!floorBounds) return
      const y = floorBounds.min.y + 0.02
      const span = Math.max(movementBoundsRef.current.x, movementBoundsRef.current.z) * 2.2
      if (guideX !== null) {
        snapGuideX = makeGuideLine("x", guideX, span, y)
        scene.add(snapGuideX)
      }
      if (guideZ !== null) {
        snapGuideZ = makeGuideLine("z", guideZ, span, y)
        scene.add(snapGuideZ)
      }
    }

    const collectWallAnchors = (excludeId: string | null) => {
      const anchorsX: number[] = [0]
      const anchorsZ: number[] = [0]
      const bounds = movementBoundsRef.current
      anchorsX.push(-bounds.x, bounds.x)
      anchorsZ.push(-bounds.z, bounds.z)
      wallRoots.forEach((root, wallId) => {
        if (excludeId && wallId === excludeId) return
        anchorsX.push(root.position.x)
        anchorsZ.push(root.position.z)
        const box = new THREE.Box3().setFromObject(root)
        const center = box.getCenter(new THREE.Vector3())
        anchorsX.push(center.x)
        anchorsZ.push(center.z)
      })
      return { anchorsX, anchorsZ }
    }

    const applyWallDragPosition = (rawX: number, rawZ: number) => {
      if (!activeWall) return
      const wallId =
        typeof activeWall.userData.wallId === "string" ? activeWall.userData.wallId : null
      const { anchorsX, anchorsZ } = collectWallAnchors(wallId)
      const snapped = snapWallPosition({
        x: rawX,
        z: rawZ,
        lockAxis: wallLockAxis,
        lockValue: wallLockValue,
        anchorsX,
        anchorsZ,
        bounds: movementBoundsRef.current,
        grid: 0.1,
        threshold: 0.12,
      })
      activeWall.position.x = snapped.x
      activeWall.position.z = snapped.z
      syncSelectionHelper(activeWall)
      updateSnapGuides(snapped.guideX, snapped.guideZ)
      if (snapped.snapped && snapped.label) {
        setMessage(`磁吸：${snapped.label}`)
      } else if (wallId) {
        setMessage(`拖动墙体 ${wallId}`)
      }
      sectionDirty = true
    }

    const applyFurnitureTransform = (value: FurnitureTransform) => {
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
      if (modeRef.current === "furniture") syncSelectionHelper(furnitureModel)
    }
    applyTransformRef.current = applyFurnitureTransform

    const commitFurnitureTransform = (next: FurnitureTransform) => {
      const bounds = movementBoundsRef.current
      const clamped: FurnitureTransform = {
        ...next,
        x: clamp(next.x, -bounds.x, bounds.x),
        z: clamp(next.z, -bounds.z, bounds.z),
        scale: clamp(next.scale, 0.5, 1.5),
      }
      transformRef.current = clamped
      applyFurnitureTransform(clamped)
      setTransform(clamped)
      return clamped
    }

    const emitFurnitureChange = (reason: FurnitureTransformChange["reason"]) => {
      const pose = layoutPoseRef.current
      const objectId = pose?.objectId || furniture?.deduplicatedObjectId || furniture?.objectId
      if (!objectId || !onTransformChangeRef.current) return
      const viewer = transformRef.current
      const layout = viewerToLayout(
        [viewer.x, baseSizeRef.current[1] * viewer.scale * 0.5, viewer.z],
        roomRef.current,
      )
      const size: [number, number, number] = [
        baseSizeRef.current[0] * viewer.scale,
        baseSizeRef.current[1] * viewer.scale,
        baseSizeRef.current[2] * viewer.scale,
      ]
      onTransformChangeRef.current({
        objectId,
        position: [layout[0], layout[1], layout[2]],
        rotation: [0, viewer.rotation, 0],
        size,
        reason,
      })
    }
    emitFurnitureChangeRef.current = emitFurnitureChange

    const updateSuggestionGhost = (pose: FurnitureLayoutPose | null) => {
      if (suggestionGhost) {
        suggestionGhost.removeFromParent()
        suggestionGhost.geometry.dispose()
        const material = suggestionGhost.material
        if (Array.isArray(material)) material.forEach((item) => item.dispose())
        else material.dispose()
        suggestionGhost = null
      }
      if (!pose || !floorBounds) return
      const viewer = layoutToViewer(pose.position, roomRef.current)
      const geometry = new THREE.BoxGeometry(pose.size[0], pose.size[1], pose.size[2])
      const material = new THREE.MeshStandardMaterial({
        color: "#d7ff67",
        transparent: true,
        opacity: 0.28,
        depthWrite: false,
      })
      suggestionGhost = new THREE.Mesh(geometry, material)
      suggestionGhost.position.set(viewer[0], pose.size[1] * 0.5 + floorBounds.min.y, viewer[2])
      suggestionGhost.rotation.y = pose.rotation[1] || 0
      suggestionGhost.name = "suggestion_ghost"
      scene.add(suggestionGhost)
    }
    applySuggestionPoseRef.current = updateSuggestionGhost

    const hitScene = () => {
      raycaster.setFromCamera(pointer, camera)
      const targets: THREE.Object3D[] = []
      if (modeRef.current === "walls") {
        wallRoots.forEach((root) => targets.push(root))
      } else if (furnitureModel) {
        targets.push(furnitureModel)
      }
      if (!targets.length) return null
      const hits = raycaster.intersectObjects(targets, true)
      return hits[0]?.object ?? null
    }

    const deleteSelectedWall = () => {
      const wallId = selectedWallIdRef.current
      if (!wallId) return false
      const root = wallRoots.get(wallId)
      if (!root) return false
      const tracker = createDisposalTracker()
      disposeObject(root, tracker)
      root.removeFromParent()
      wallRoots.delete(wallId)
      fadeWalls.delete(wallId)
      if (sectionIndex) {
        sectionIndex.groups.delete(wallId)
        sectionIndex.wallMeshes = sectionIndex.wallMeshes.filter(
          (mesh) => sectionIndex?.meshToWallId.get(mesh) !== wallId,
        )
        for (const [mesh, id] of [...sectionIndex.meshToWallId.entries()]) {
          if (id === wallId) sectionIndex.meshToWallId.delete(mesh)
        }
      }
      selectWall(null)
      setWallCount(wallRoots.size)
      setMessage(`已删除 ${wallId} · 剩余 ${wallRoots.size} 堵墙`)
      return true
    }
    deleteSelectedWallRef.current = deleteSelectedWall

    const exportHouse = () =>
      new Promise<ArrayBuffer>((resolve, reject) => {
        if (!floorModel) {
          reject(new Error("户型尚未加载"))
          return
        }
        // 导出时临时隐藏家具与选中框
        const furnitureVisible = furnitureModel?.visible ?? false
        const helperVisible = selectionHelper?.visible ?? false
        if (furnitureModel) furnitureModel.visible = false
        if (selectionHelper) selectionHelper.visible = false
        if (grid) grid.visible = false

        new GLTFExporter().parse(
          floorModel,
          (result) => {
            if (furnitureModel) furnitureModel.visible = furnitureVisible
            if (selectionHelper) selectionHelper.visible = helperVisible
            if (grid) grid.visible = true
            if (result instanceof ArrayBuffer) resolve(result)
            else reject(new Error("导出结果不是二进制 GLB"))
          },
          (error) => {
            if (furnitureModel) furnitureModel.visible = furnitureVisible
            if (selectionHelper) selectionHelper.visible = helperVisible
            if (grid) grid.visible = true
            reject(error instanceof Error ? error : new Error("导出 GLB 失败"))
          },
          { binary: true },
        )
      })
    exportHouseRef.current = exportHouse

    const onPointerDown = (event: PointerEvent) => {
      if (event.button !== 0 || !floorBounds) return
      setPointerFromEvent(event)
      const hit = hitScene()

      if (modeRef.current === "walls") {
        const wall = findEditableWall(hit)
        if (!wall) {
          selectWall(null)
          return
        }
        event.preventDefault()
        event.stopImmediatePropagation()
        selectWall(wall)
        isDragging = true
        dragKind = "wall"
        setDragging(true)
        controls.enabled = false
        renderer.domElement.setPointerCapture(event.pointerId)
        const wallSize = new THREE.Box3().setFromObject(wall).getSize(new THREE.Vector3())
        wallLockAxis = inferWallLockAxis(wallSize.x, wallSize.z)
        wallLockValue = wallLockAxis === "x" ? wall.position.x : wall.position.z
        groundPlane.constant = -floorBounds.min.y
        raycaster.setFromCamera(pointer, camera)
        if (raycaster.ray.intersectPlane(groundPlane, planeHit)) {
          dragOffset.set(wall.position.x - planeHit.x, 0, wall.position.z - planeHit.z)
        } else {
          dragOffset.set(0, 0, 0)
        }
        const lockHint =
          wallLockAxis === "x"
            ? "（东西向墙，仅前后磁吸移动）"
            : wallLockAxis === "z"
              ? "（南北向墙，仅左右磁吸移动）"
              : "（自由移动 + 磁吸）"
        setMessage(`拖动墙体 ${wall.userData.wallId}${lockHint}`)
        renderer.domElement.style.cursor = "grabbing"
        return
      }

      if (!furnitureModel || !hit) {
        syncSelectionHelper(null)
        return
      }
      event.preventDefault()
      event.stopImmediatePropagation()
      isDragging = true
      dragKind = "furniture"
      setDragging(true)
      controls.enabled = false
      renderer.domElement.setPointerCapture(event.pointerId)
      syncSelectionHelper(furnitureModel)
      groundPlane.constant = -floorBounds.min.y
      raycaster.setFromCamera(pointer, camera)
      if (raycaster.ray.intersectPlane(groundPlane, planeHit)) {
        dragOffset.set(
          transformRef.current.x - planeHit.x,
          0,
          transformRef.current.z - planeHit.z,
        )
      } else {
        dragOffset.set(0, 0, 0)
      }
      setMessage("拖动家具中 · 松开放置")
      renderer.domElement.style.cursor = "grabbing"
    }

    const onPointerMove = (event: PointerEvent) => {
      setPointerFromEvent(event)
      if (!isDragging || !floorBounds) {
        const hit = hitScene()
        const over =
          modeRef.current === "walls" ? Boolean(findEditableWall(hit)) : Boolean(hit)
        renderer.domElement.style.cursor = over ? "grab" : "grab"
        return
      }
      event.preventDefault()
      raycaster.setFromCamera(pointer, camera)
      groundPlane.constant = -floorBounds.min.y
      if (!raycaster.ray.intersectPlane(groundPlane, planeHit)) return

      if (dragKind === "wall" && activeWall) {
        applyWallDragPosition(planeHit.x + dragOffset.x, planeHit.z + dragOffset.z)
        return
      }

      if (dragKind === "furniture") {
        commitFurnitureTransform({
          ...transformRef.current,
          x: planeHit.x + dragOffset.x,
          z: planeHit.z + dragOffset.z,
        })
        sectionDirty = true
      }
    }

    const endDrag = (event: PointerEvent) => {
      if (!isDragging) return
      const finishedKind = dragKind
      isDragging = false
      dragKind = null
      wallLockAxis = null
      setDragging(false)
      controls.enabled = true
      clearSnapGuides()
      try {
        renderer.domElement.releasePointerCapture(event.pointerId)
      } catch {
        // ignore
      }
      if (finishedKind === "furniture") {
        emitFurnitureChange("drag")
        setMessage("已更新位姿 · 正在做空间检测…")
      } else if (finishedKind === "wall") {
        setMessage("墙体已放置（已磁吸对齐）· 可继续拖动或 Delete 删除")
      } else {
        setMessage(modeHint())
      }
      renderer.domElement.style.cursor = "grab"
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (modeRef.current !== "walls") return
      if (event.key === "Delete" || event.key === "Backspace") {
        const tag = (event.target as HTMLElement | null)?.tagName
        if (tag === "INPUT" || tag === "TEXTAREA") return
        event.preventDefault()
        deleteSelectedWall()
      }
    }

    renderer.domElement.addEventListener("pointerdown", onPointerDown, true)
    renderer.domElement.addEventListener("pointermove", onPointerMove)
    renderer.domElement.addEventListener("pointerup", endDrag)
    renderer.domElement.addEventListener("pointercancel", endDrag)
    window.addEventListener("keydown", onKeyDown)

    const evaluateAutoSection = () => {
      if (!autoSection || !sectionIndex || modeRef.current === "walls") {
        fadeWalls.forEach((wall) => {
          wall.target = 1
        })
        return
      }
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

    const buildEditableWalls = (root: THREE.Object3D, index: WallSectionIndex) => {
      wallRoots.clear()
      index.groups.forEach((group, wallId) => {
        const wallRoot = new THREE.Group()
        wallRoot.name = `editable_${wallId}`
        wallRoot.userData.rombotKind = "editableWall"
        wallRoot.userData.wallId = wallId
        root.add(wallRoot)
        ;[...group.wallMeshes, ...group.fixtureMeshes].forEach((mesh) => {
          wallRoot.attach(mesh)
        })
        wallRoots.set(wallId, wallRoot)
      })
      setWallCount(wallRoots.size)
    }

    const loadFurniture = () => {
      if (!furniture || !floorBounds) {
        setStatus("ready")
        setMessage(modeHint())
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
          const initialPose = layoutPoseRef.current
          if (initialPose) {
            const viewer = layoutToViewer(initialPose.position, roomRef.current)
            const base = baseSizeRef.current
            const scale =
              base[0] > 1e-6 ? initialPose.size[0] / base[0] : 1
            commitFurnitureTransform({
              x: viewer[0],
              z: viewer[2],
              rotation: initialPose.rotation[1] || 0,
              scale: clamp(scale, 0.5, 1.5),
            })
          } else {
            applyFurnitureTransform(INITIAL_TRANSFORM)
          }
          setFurnitureReady(true)
          setStatus("ready")
          setMode("furniture")
          setMessage(modeHint())
          updateSuggestionGhost(null)
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

        sectionIndex = createWallSectionIndex(floorModel)
        buildEditableWalls(floorModel, sectionIndex)
        if (autoSection) {
          sectionIndex.groups.forEach((group, wallId) => {
            fadeWalls.set(wallId, prepareFadeWall(group, orphanedMaterials))
          })
        }
        sectionDirty = true

        floorBounds = new THREE.Box3().setFromObject(floorModel)
        movementBoundsRef.current = {
          x: Math.max(size.x / 2 - 0.25, 0),
          z: Math.max(size.z / 2 - 0.25, 0),
        }

        const radius = Math.max(size.x, size.y, size.z, 1)
        camera.near = Math.max(radius / 1000, 0.01)
        camera.far = radius * 100
        camera.position.set(radius * 0.35, radius * 1.55, radius * 0.55)
        camera.updateProjectionMatrix()
        controls.target.set(0, 0, 0)
        controls.minDistance = radius * 0.35
        controls.maxDistance = radius * 5
        controls.update()

        grid = new THREE.GridHelper(radius * 2.6, 24, "#6f7e52", "#293025")
        grid.position.y = floorBounds.min.y - 0.01
        scene.add(grid)

        selectionHelper = new THREE.BoxHelper(floorModel, "#d7ff67")
        selectionHelper.visible = false
        scene.add(selectionHelper)

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
      if (selectionHelper?.visible) selectionHelper.update()
      renderer.render(scene, camera)
      frameId = window.requestAnimationFrame(render)
    }
    render()

    return () => {
      disposed = true
      applyTransformRef.current = null
      exportHouseRef.current = null
      deleteSelectedWallRef.current = null
      emitFurnitureChangeRef.current = null
      applySuggestionPoseRef.current = null
      clearSnapGuides()
      delete container.dataset.sectionWall
      window.cancelAnimationFrame(frameId)
      resizeObserver.disconnect()
      renderer.domElement.removeEventListener("pointerdown", onPointerDown, true)
      renderer.domElement.removeEventListener("pointermove", onPointerMove)
      renderer.domElement.removeEventListener("pointerup", endDrag)
      renderer.domElement.removeEventListener("pointercancel", endDrag)
      window.removeEventListener("keydown", onKeyDown)
      controls.removeEventListener("change", markSectionDirty)
      controls.dispose()
      const tracker = createDisposalTracker()
      if (floorModel) disposeObject(floorModel, tracker)
      if (furnitureModel) disposeObject(furnitureModel, tracker)
      if (suggestionGhost) {
        suggestionGhost.geometry.dispose()
        const material = suggestionGhost.material
        if (Array.isArray(material)) material.forEach((item) => item.dispose())
        else material.dispose()
      }
      orphanedMaterials.forEach((material) => disposeMaterial(material, tracker))
      if (selectionHelper) {
        selectionHelper.geometry.dispose()
        disposeMaterial(selectionHelper.material as THREE.Material, tracker)
      }
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

  useEffect(() => {
    if (status !== "ready" || !layoutPose || dragging) return
    const viewer = layoutToViewer(layoutPose.position, { width: roomWidth, depth: roomDepth })
    const base = baseSizeRef.current
    const scale = base[0] > 1e-6 ? layoutPose.size[0] / base[0] : 1
    const next = {
      x: viewer[0],
      z: viewer[2],
      rotation: layoutPose.rotation[1] || 0,
      scale: clamp(scale, 0.5, 1.5),
    }
    transformRef.current = next
    applyTransformRef.current?.(next)
    setTransform(next)
  }, [dragging, layoutPose, roomDepth, roomWidth, status])

  useEffect(() => {
    applySuggestionPoseRef.current?.(suggestionPose ?? null)
  }, [suggestionPose, status])

  useEffect(() => {
    if (status !== "ready" || dragging) return
    setMessage(
      mode === "walls"
        ? "编辑墙体：拖动自动磁吸网格/墙线 · Delete 删除 · 空白处旋转"
        : furniture
          ? "摆放家具：拖动结束后自动几何检测"
          : "拖动旋转视角 · 滚轮缩放",
    )
  }, [dragging, furniture, mode, status])

  const updateFurniture = (
    updater: (current: FurnitureTransform) => FurnitureTransform,
    reason: FurnitureTransformChange["reason"] = "rotate",
  ) => {
    setTransform((current) => {
      const proposed = updater(current)
      const bounds = movementBoundsRef.current
      const next = {
        ...proposed,
        x: clamp(proposed.x, -bounds.x, bounds.x),
        z: clamp(proposed.z, -bounds.z, bounds.z),
        scale: clamp(proposed.scale, 0.5, 1.5),
      }
      transformRef.current = next
      applyTransformRef.current?.(next)
      queueMicrotask(() => emitFurnitureChangeRef.current?.(reason))
      return next
    })
  }

  const handleExport = async () => {
    if (!exportHouseRef.current) return
    setBusyAction("export")
    try {
      const buffer = await exportHouseRef.current()
      downloadArrayBuffer(buffer, `${sceneId || "floorplan"}_edited.glb`)
      setMessage("已下载编辑后的户型 GLB")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "导出失败")
    } finally {
      setBusyAction(null)
    }
  }

  const handleSaveLocal = async () => {
    if (!exportHouseRef.current || !sceneId) {
      setMessage("当前没有 sceneId，无法覆盖本地预设，请先导出下载")
      return
    }
    setBusyAction("save")
    try {
      const buffer = await exportHouseRef.current()
      await saveFloorplanWhitebox(sceneId, buffer)
      setMessage(`已覆盖本地 ${sceneId}/whitebox.glb，刷新即可生效`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "保存失败")
    } finally {
      setBusyAction(null)
    }
  }

  return (
    <div
      className="floorplan-viewer floorplan-viewer--sandbox"
      data-status={status}
      data-mode={mode}
      data-dragging={dragging ? "true" : "false"}
    >
      <div ref={containerRef} className="floorplan-viewer__canvas" />

      <div className="sandbox-toolbar" role="toolbar" aria-label="沙盒工具">
        <div className="sandbox-toolbar__modes">
          <button
            type="button"
            className={mode === "walls" ? "is-active" : ""}
            onClick={() => setMode("walls")}
          >
            编辑墙体
          </button>
          <button
            type="button"
            className={mode === "furniture" ? "is-active" : ""}
            onClick={() => setMode("furniture")}
            disabled={!furniture}
            title={furniture ? "摆放家具" : "先从 Feed 选家具"}
          >
            摆放家具
          </button>
        </div>
        <div className="sandbox-toolbar__actions">
          <button
            type="button"
            disabled={mode !== "walls" || !selectedWallId}
            onClick={() => deleteSelectedWallRef.current?.()}
          >
            删除墙体
          </button>
          <button type="button" disabled={busyAction !== null} onClick={() => void handleExport()}>
            {busyAction === "export" ? "导出中…" : "导出 GLB"}
          </button>
          <button
            type="button"
            disabled={!sceneId || busyAction !== null}
            onClick={() => void handleSaveLocal()}
            title={sceneId ? `覆盖 sample_data/.../${sceneId}/whitebox.glb` : "缺少 sceneId"}
          >
            {busyAction === "save" ? "保存中…" : "保存到本地"}
          </button>
        </div>
      </div>

      <div className="floorplan-viewer__status" role="status">
        <span className={status === "loading" ? "viewer-spinner" : ""} />
        {message}
        {mode === "walls" && status === "ready" ? ` · ${wallCount} 堵墙` : ""}
        {selectedWallId ? ` · 选中 ${selectedWallId}` : ""}
      </div>

      {mode === "furniture" && furniture && furnitureReady && (
        <div className="furniture-controls" aria-label="旋转与缩放家具">
          <div className="furniture-controls__hint">
            {dragging ? "拖动中" : "可拖动家具"}
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
            >
              ↶ 旋转
            </button>
            <button
              type="button"
              onClick={() =>
                updateFurniture((value) => ({
                  ...value,
                  rotation: value.rotation + Math.PI / 12,
                }))
              }
            >
              ↷
            </button>
            <button
              type="button"
              onClick={() =>
                updateFurniture(
                  (value) => ({ ...value, scale: value.scale - 0.1 }),
                  "scale",
                )
              }
            >
              −
            </button>
            <button
              type="button"
              onClick={() =>
                updateFurniture(
                  (value) => ({ ...value, scale: value.scale + 0.1 }),
                  "scale",
                )
              }
            >
              ＋
            </button>
            <button
              type="button"
              onClick={() => updateFurniture(() => INITIAL_TRANSFORM, "reset")}
            >
              重置
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
