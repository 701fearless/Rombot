import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { AUTO_SECTION_RAY_SAMPLES, createWallSectionIndex, selectSectionWall } from '@/lib/autoSection'
import { snapWallPosition } from '@/lib/wallSnap'
import type { SceneSnapshot, SnapshotObject, SnapshotWall, Vector3 } from '@/types/scene'

interface Props {
  snapshot: SceneSnapshot
  selectedId: string
  wallMode: boolean
  onSelect: (id: string) => void
  onObjectTransform: (id: string, position: Vector3) => void
  onWallChange: (wall: SnapshotWall) => void
  onReady?: (wallRoot: THREE.Group) => void
}

function material(color: number, opacity = 1) { return new THREE.MeshStandardMaterial({ color, roughness: .78, metalness: .01, transparent: opacity < 1, opacity }) }
function bounds(snapshot: SceneSnapshot) {
  const xs = snapshot.room.floorPolygon.map(([x]) => x); const zs = snapshot.room.floorPolygon.map(([, z]) => z)
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minZ: Math.min(...zs), maxZ: Math.max(...zs) }
}
function pointSegmentDistance(point: [number, number], start: [number, number], end: [number, number]) {
  const dx = end[0] - start[0]; const dz = end[1] - start[1]; const lengthSq = dx * dx + dz * dz
  if (lengthSq < 1e-8) return Math.hypot(point[0] - start[0], point[1] - start[1])
  const amount = Math.max(0, Math.min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dz) / lengthSq))
  return Math.hypot(point[0] - (start[0] + amount * dx), point[1] - (start[1] + amount * dz))
}
function outerWallIds(snapshot: SceneSnapshot) {
  const polygon = snapshot.room.floorPolygon; const edges = polygon.map((point, index) => [point, polygon[(index + 1) % polygon.length]] as const)
  return new Set(snapshot.room.walls.filter((wall) => [wall.start, wall.end].every((point) => edges.some(([start, end]) => pointSegmentDistance(point, start, end) <= .18))).map((wall) => wall.id))
}
function wallMesh(wall: SnapshotWall) {
  const [sx, sz] = wall.start; const [ex, ez] = wall.end; const length = Math.hypot(ex - sx, ez - sz); const mesh = new THREE.Mesh(new THREE.BoxGeometry(length, wall.height, wall.thickness ?? .12), material(0xe5e0d5, .86))
  mesh.position.set((sx + ex) / 2, wall.height / 2, (sz + ez) / 2); mesh.rotation.y = -Math.atan2(ez - sz, ex - sx); mesh.name = wall.id; mesh.userData = { kind: 'wall', id: wall.id, rombotKind: 'wall', wallId: wall.id }; mesh.castShadow = true; mesh.receiveShadow = true
  return mesh
}
function fallbackObject(item: SnapshotObject) {
  const [w, h, d] = item.geometry.size; const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material(item.source.type === 'upload' ? 0xd6a55b : 0x7e9b8f)); mesh.position.y = 0; mesh.castShadow = true; mesh.receiveShadow = true; return mesh
}
function normalizeModel(root: THREE.Object3D, size: Vector3) {
  const box = new THREE.Box3().setFromObject(root); const actual = box.getSize(new THREE.Vector3()); if (actual.x < 1e-5 || actual.y < 1e-5 || actual.z < 1e-5) throw new Error('empty model')
  root.scale.set(size[0] / actual.x, size[1] / actual.y, size[2] / actual.z); root.updateMatrixWorld(true)
  const fitted = new THREE.Box3().setFromObject(root); const center = fitted.getCenter(new THREE.Vector3()); root.position.add(new THREE.Vector3(-center.x, -center.y, -center.z))
  root.traverse((child) => { if (child instanceof THREE.Mesh) { child.castShadow = true; child.receiveShadow = true } })
}

export function SceneEditor3D({ snapshot, selectedId, wallMode, onSelect, onObjectTransform, onWallChange, onReady }: Props) {
  const hostRef = useRef<HTMLDivElement>(null); const onSelectRef = useRef(onSelect); const objectRef = useRef(onObjectTransform); const wallRef = useRef(onWallChange); const selectedRef = useRef(selectedId); const wallModeRef = useRef(wallMode)
  useEffect(() => { onSelectRef.current = onSelect; objectRef.current = onObjectTransform; wallRef.current = onWallChange; selectedRef.current = selectedId; wallModeRef.current = wallMode }, [onSelect, onObjectTransform, onWallChange, selectedId, wallMode])
  useEffect(() => {
    const host = hostRef.current; if (!host) return
    let disposed = false; let animation = 0; const scene = new THREE.Scene(); scene.background = new THREE.Color(0xe9eae6); scene.fog = new THREE.Fog(0xe9eae6, 16, 32)
    const camera = new THREE.PerspectiveCamera(42, 1, .05, 80); const b = bounds(snapshot); const width = b.maxX - b.minX; const depth = b.maxZ - b.minZ; const radius = Math.max(width, depth, 1); const center = new THREE.Vector3((b.minX + b.maxX) / 2, 0, (b.minZ + b.maxZ) / 2); camera.position.set(center.x + radius * 1.08, radius * .9, center.z + radius * 1.08)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true }); renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05; host.appendChild(renderer.domElement)
    const controls = new OrbitControls(camera, renderer.domElement); controls.target.set(center.x, .35, center.z); controls.enableDamping = true; controls.dampingFactor = .08; controls.minPolarAngle = .18; controls.maxPolarAngle = Math.PI / 2.03; controls.minDistance = 2; controls.maxDistance = 20
    scene.add(new THREE.HemisphereLight(0xffffff, 0xa7aca2, 1.8)); const sun = new THREE.DirectionalLight(0xffffff, 2.7); sun.position.set(center.x + 7, 12, center.z + 8); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -radius * 1.4; sun.shadow.camera.right = radius * 1.4; sun.shadow.camera.top = radius * 1.4; sun.shadow.camera.bottom = -radius * 1.4; sun.shadow.bias = -.0004; sun.shadow.normalBias = .025; scene.add(sun); const fill = new THREE.DirectionalLight(0xe4e8df, .75); fill.position.set(center.x - 8, 5, center.z - 4); scene.add(fill)
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(width, depth), material(0xd4d6cf)); floor.rotation.x = -Math.PI / 2; floor.position.set(center.x, 0, center.z); floor.receiveShadow = true; floor.userData.kind = 'floor'; scene.add(floor)
    const grid = new THREE.GridHelper(Math.max(width, depth), 20, 0x899087, 0xb8bcb3); grid.position.set(center.x, .004, center.z); const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material]; gridMaterials.forEach((item) => { item.transparent = true; item.opacity = .56 }); scene.add(grid)
    const whiteboxRoot = new THREE.Group(); whiteboxRoot.name = 'editable_whitebox'; scene.add(whiteboxRoot)
    snapshot.room.walls.forEach((wall) => whiteboxRoot.add(wallMesh(wall))); onReady?.(whiteboxRoot)
    const whiteboxUrl = snapshot.room.whiteboxGlbUrl; let referenceSection: ReturnType<typeof createWallSectionIndex> | null = null
    if (whiteboxUrl) new GLTFLoader().load(whiteboxUrl, ({ scene: model }) => { if (disposed) return; model.name = 'reference_whitebox'; model.traverse((child) => { if (child instanceof THREE.Mesh) { child.material = material(0xc8c2b6, .12); child.castShadow = false; child.receiveShadow = true } }); scene.add(model); referenceSection = createWallSectionIndex(model) }, undefined, () => undefined)
    const objectRoots = new Map<string, THREE.Group>(); const loader = new GLTFLoader()
    snapshot.objects.forEach((item) => {
      const wrapper = new THREE.Group(); wrapper.userData = { kind: 'furniture', id: item.instanceId }; wrapper.name = item.instanceId; wrapper.position.fromArray(item.transform.position); wrapper.rotation.fromArray(item.transform.rotation); wrapper.scale.fromArray(item.transform.scale); scene.add(wrapper); objectRoots.set(item.instanceId, wrapper)
      if (item.geometry.glbUrl) loader.load(item.geometry.glbUrl, ({ scene: model }) => { if (disposed) return; try { normalizeModel(model, item.geometry.size); wrapper.add(model) } catch { wrapper.add(fallbackObject(item)) } }, undefined, () => { if (!disposed) wrapper.add(fallbackObject(item)) })
      else wrapper.add(fallbackObject(item))
    })
    const outline = new THREE.Box3Helper(new THREE.Box3(), 0xd9ed63); scene.add(outline); outline.visible = false
    const raycaster = new THREE.Raycaster(); const pointer = new THREE.Vector2(); const dragPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0); let dragging: { kind: 'furniture' | 'wall'; id: string; offset: THREE.Vector3; start?: SnapshotWall } | null = null
    const pointerNdc = (event: PointerEvent) => { const rect = renderer.domElement.getBoundingClientRect(); pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1) }
    const rootData = (object: THREE.Object3D | null): { kind?: string; id?: string } => { let current = object; while (current) { if (current.userData.kind) return current.userData as { kind?: string; id?: string }; current = current.parent } return {} }
    const onDown = (event: PointerEvent) => { pointerNdc(event); raycaster.setFromCamera(pointer, camera); const candidates = wallModeRef.current ? [...whiteboxRoot.children] : [...objectRoots.values()]; const hit = raycaster.intersectObjects(candidates, true)[0]; if (!hit) { onSelectRef.current(''); return } const data = rootData(hit.object); if (!data.id) return; onSelectRef.current(data.id); const point = new THREE.Vector3(); if (!raycaster.ray.intersectPlane(dragPlane, point)) return; controls.enabled = false; renderer.domElement.setPointerCapture(event.pointerId)
      if (data.kind === 'furniture') { const root = objectRoots.get(data.id); if (root) dragging = { kind: 'furniture', id: data.id, offset: root.position.clone().sub(point) } }
      else { const source = snapshot.room.walls.find((wall) => wall.id === data.id); if (source) dragging = { kind: 'wall', id: data.id, offset: new THREE.Vector3((source.start[0] + source.end[0]) / 2 - point.x, 0, (source.start[1] + source.end[1]) / 2 - point.z), start: source } }
    }
    const onMove = (event: PointerEvent) => { if (!dragging) return; pointerNdc(event); raycaster.setFromCamera(pointer, camera); const point = new THREE.Vector3(); if (!raycaster.ray.intersectPlane(dragPlane, point)) return
      if (dragging.kind === 'furniture') { const root = objectRoots.get(dragging.id); if (!root) return; const item = snapshot.objects.find((x) => x.instanceId === dragging?.id); if (!item) return; const halfX = item.geometry.size[0] * item.transform.scale[0] / 2; const halfZ = item.geometry.size[2] * item.transform.scale[2] / 2; root.position.x = Math.round(Math.max(b.minX + halfX, Math.min(b.maxX - halfX, point.x + dragging.offset.x)) * 10) / 10; root.position.z = Math.round(Math.max(b.minZ + halfZ, Math.min(b.maxZ - halfZ, point.z + dragging.offset.z)) * 10) / 10 }
      else if (dragging.start) { const start = dragging.start; const cx = point.x + dragging.offset.x; const cz = point.z + dragging.offset.z; const originalX = (start.start[0] + start.end[0]) / 2; const originalZ = (start.start[1] + start.end[1]) / 2; const snap = snapWallPosition({ x: cx, z: cz, bounds: { x: width / 2, z: depth / 2 }, anchorsX: snapshot.room.walls.flatMap((w) => [w.start[0], w.end[0]]), anchorsZ: snapshot.room.walls.flatMap((w) => [w.start[1], w.end[1]]) }); const dx = snap.x - originalX; const dz = snap.z - originalZ; const mesh = whiteboxRoot.children.find((child) => child.userData.id === dragging?.id); if (mesh) mesh.position.set(snap.x, mesh.position.y, snap.z); (dragging as typeof dragging & { next?: SnapshotWall }).next = { ...start, start: [start.start[0] + dx, start.start[1] + dz], end: [start.end[0] + dx, start.end[1] + dz] } }
    }
    const onUp = (event: PointerEvent) => { if (!dragging) return; if (dragging.kind === 'furniture') { const root = objectRoots.get(dragging.id); const item = snapshot.objects.find((x) => x.instanceId === dragging?.id); if (root && item) objectRef.current(dragging.id, [root.position.x, item.transform.position[1], root.position.z]) } else { const next = (dragging as typeof dragging & { next?: SnapshotWall }).next; if (next) wallRef.current(next) } dragging = null; controls.enabled = true; if (renderer.domElement.hasPointerCapture(event.pointerId)) renderer.domElement.releasePointerCapture(event.pointerId) }
    renderer.domElement.addEventListener('pointerdown', onDown); renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('pointerup', onUp); renderer.domElement.addEventListener('pointercancel', onUp)
    const section = createWallSectionIndex(whiteboxRoot); const exteriorIds = outerWallIds(snapshot); const exteriorMeshes = section.wallMeshes.filter((mesh) => { const id = section.meshToWallId.get(mesh); return id ? exteriorIds.has(id) : false }); const sectionMeshes = exteriorMeshes.length ? exteriorMeshes : section.wallMeshes; const sectionGroups = exteriorMeshes.length ? new Map([...section.groups].filter(([id]) => exteriorIds.has(id))) : section.groups; const view = new THREE.Vector3(); let sectioned: string | null = null
    const resize = () => { const widthPx = host.clientWidth; const heightPx = host.clientHeight; renderer.setSize(widthPx, heightPx, false); camera.aspect = widthPx / Math.max(heightPx, 1); camera.updateProjectionMatrix() }; const observer = new ResizeObserver(resize); observer.observe(host); resize()
    const animate = () => { animation = requestAnimationFrame(animate); controls.update(); const activeId = selectedRef.current; const selected = objectRoots.get(activeId) ?? whiteboxRoot.children.find((x) => x.userData.id === activeId); if (selected) { outline.box.setFromObject(selected); outline.visible = true } else outline.visible = false
      const hits = AUTO_SECTION_RAY_SAMPLES.flatMap((sample) => { raycaster.setFromCamera(sample, camera); const hit = raycaster.intersectObjects(sectionMeshes, false)[0]; const wallId = hit ? section.meshToWallId.get(hit.object) : undefined; return wallId && hit ? [{ wallId, distance: hit.distance }] : [] }); camera.getWorldDirection(view); const selectedWall = selectSectionWall({ hits, groups: sectionGroups, viewDirectionXZ: new THREE.Vector2(view.x, view.z), polarAngle: Math.acos(Math.max(-1, Math.min(1, view.y))), cameraTargetDistance: camera.position.distanceTo(controls.target), currentWallId: sectioned }); sectioned = wallModeRef.current ? null : selectedWall?.wallId ?? null; section.groups.forEach((group, id) => group.wallMeshes.forEach((mesh) => { const mat = mesh.material as THREE.MeshStandardMaterial; const targetOpacity = id === sectioned ? 0 : wallModeRef.current ? .94 : .86; const nextOpacity = mat.opacity + (targetOpacity - mat.opacity) * .16; mat.opacity = Math.abs(nextOpacity - targetOpacity) < .008 ? targetOpacity : nextOpacity; mat.transparent = mat.opacity < .999; mat.depthWrite = mat.opacity > .55 })); referenceSection?.groups.forEach((group, id) => [...group.wallMeshes, ...group.fixtureMeshes].forEach((mesh) => { const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]; materials.forEach((mat) => { const targetOpacity = id === sectioned ? 0 : .12; const nextOpacity = mat.opacity + (targetOpacity - mat.opacity) * .16; mat.opacity = Math.abs(nextOpacity - targetOpacity) < .008 ? targetOpacity : nextOpacity; mat.transparent = true; mat.depthWrite = false }) })); renderer.render(scene, camera) }
    animate()
    return () => { disposed = true; cancelAnimationFrame(animation); observer.disconnect(); renderer.domElement.removeEventListener('pointerdown', onDown); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('pointerup', onUp); renderer.domElement.removeEventListener('pointercancel', onUp); controls.dispose(); renderer.dispose(); scene.traverse((object) => { if (object instanceof THREE.Mesh) { object.geometry.dispose(); const mats = Array.isArray(object.material) ? object.material : [object.material]; mats.forEach((m) => m.dispose()) } }); renderer.domElement.remove() }
  }, [snapshot, onReady])
  return <div className='scene-editor-canvas' ref={hostRef} data-testid='scene-canvas' />
}
