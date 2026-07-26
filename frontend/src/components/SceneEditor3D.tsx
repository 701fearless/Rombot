import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { AUTO_SECTION_RAY_SAMPLES, createWallSectionIndex, selectFrontmostSectionWall } from '@/lib/autoSection'
import type { SceneSnapshot, SnapshotObject, Vector3 } from '@/types/scene'

interface Props {
  snapshot: SceneSnapshot
  selectedId: string
  onSelect: (id: string) => void
  onObjectTransform: (
    id: string,
    transform: Pick<SnapshotObject['transform'], 'position' | 'rotation'>,
    placement: Pick<SnapshotObject['placement'], 'surface' | 'supportObjectId'>,
  ) => void
}

type SurfaceKind = 'floor' | 'wall' | 'object'
type PlacementResult = { position: Vector3; rotation: Vector3; surface: SurfaceKind; supportObjectId: string | null; wallId: string | null }

function material(color: number, opacity = 1) { return new THREE.MeshStandardMaterial({ color, roughness: .78, metalness: .01, transparent: opacity < 1, opacity }) }
function bounds(snapshot: SceneSnapshot) {
  const xs = snapshot.room.floorPolygon.map(([x]) => x); const zs = snapshot.room.floorPolygon.map(([, z]) => z)
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minZ: Math.min(...zs), maxZ: Math.max(...zs) }
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

function worldNormal(hit: THREE.Intersection<THREE.Object3D>) {
  if (!hit.face) return null
  return hit.face.normal.clone().applyMatrix3(new THREE.Matrix3().getNormalMatrix(hit.object.matrixWorld)).normalize()
}

function objectBounds(item: SnapshotObject, position = item.transform.position, rotation = item.transform.rotation) {
  const width = item.geometry.size[0] * item.transform.scale[0]
  const height = item.geometry.size[1] * item.transform.scale[1]
  const depth = item.geometry.size[2] * item.transform.scale[2]
  const cosine = Math.abs(Math.cos(rotation[1])); const sine = Math.abs(Math.sin(rotation[1]))
  const halfX = (width * cosine + depth * sine) / 2; const halfZ = (width * sine + depth * cosine) / 2; const halfY = height / 2
  return new THREE.Box3(
    new THREE.Vector3(position[0] - halfX, position[1] - halfY, position[2] - halfZ),
    new THREE.Vector3(position[0] + halfX, position[1] + halfY, position[2] + halfZ),
  )
}

function overlaps(left: THREE.Box3, right: THREE.Box3, tolerance = .015) {
  return left.min.x < right.max.x - tolerance && left.max.x > right.min.x + tolerance
    && left.min.y < right.max.y - tolerance && left.max.y > right.min.y + tolerance
    && left.min.z < right.max.z - tolerance && left.max.z > right.min.z + tolerance
}

export function SceneEditor3D({ snapshot, selectedId, onSelect, onObjectTransform }: Props) {
  const hostRef = useRef<HTMLDivElement>(null); const onSelectRef = useRef(onSelect); const objectRef = useRef(onObjectTransform); const selectedRef = useRef(selectedId); const snapshotRef = useRef(snapshot); const objectRootsRef = useRef(new Map<string, THREE.Group>()); const cameraViewRef = useRef<{ sceneId: string; position: Vector3; target: Vector3 } | null>(null)
  const structureKey = snapshot.objects.map((item) => `${item.instanceId}:${item.geometry.glbUrl ?? ''}:${item.geometry.size.join(',')}`).join('|')
  const roomKey = `${snapshot.sceneId}:${snapshot.room.whiteboxGlbUrl}:${snapshot.room.floorPolygon.flat().join(',')}`
  useEffect(() => { onSelectRef.current = onSelect; objectRef.current = onObjectTransform; selectedRef.current = selectedId }, [onSelect, onObjectTransform, selectedId])
  useEffect(() => {
    snapshotRef.current = snapshot
    snapshot.objects.forEach((item) => {
      const root = objectRootsRef.current.get(item.instanceId)
      if (!root) return
      root.position.fromArray(item.transform.position)
      root.rotation.fromArray(item.transform.rotation)
      root.scale.fromArray(item.transform.scale)
      root.updateMatrixWorld(true)
    })
  }, [snapshot])
  useEffect(() => {
    const host = hostRef.current; if (!host) return
    let disposed = false; let animation = 0; const scene = new THREE.Scene(); scene.background = new THREE.Color(0xe9eae6); scene.fog = new THREE.Fog(0xe9eae6, 16, 32)
    const camera = new THREE.PerspectiveCamera(42, 1, .05, 80); const b = bounds(snapshot); const width = b.maxX - b.minX; const depth = b.maxZ - b.minZ; const radius = Math.max(width, depth, 1); const center = new THREE.Vector3((b.minX + b.maxX) / 2, 0, (b.minZ + b.maxZ) / 2); const savedView = cameraViewRef.current?.sceneId === snapshot.sceneId ? cameraViewRef.current : null; if (savedView) camera.position.fromArray(savedView.position); else camera.position.set(center.x + radius * 1.08, radius * .9, center.z + radius * 1.08)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, preserveDrawingBuffer: true }); renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05; host.appendChild(renderer.domElement)
    const controls = new OrbitControls(camera, renderer.domElement); if (savedView) controls.target.fromArray(savedView.target); else controls.target.set(center.x, .35, center.z); controls.enableDamping = true; controls.dampingFactor = .08; controls.minPolarAngle = .18; controls.maxPolarAngle = Math.PI / 2.03; controls.minDistance = 2; controls.maxDistance = 20
    const rememberCamera = () => { cameraViewRef.current = { sceneId: snapshot.sceneId, position: camera.position.toArray() as Vector3, target: controls.target.toArray() as Vector3 } }; controls.addEventListener('change', rememberCamera); rememberCamera()
    scene.add(new THREE.HemisphereLight(0xffffff, 0xa7aca2, 1.8)); const sun = new THREE.DirectionalLight(0xffffff, 2.7); sun.position.set(center.x + 7, 12, center.z + 8); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -radius * 1.4; sun.shadow.camera.right = radius * 1.4; sun.shadow.camera.top = radius * 1.4; sun.shadow.camera.bottom = -radius * 1.4; sun.shadow.bias = -.0004; sun.shadow.normalBias = .025; scene.add(sun); const fill = new THREE.DirectionalLight(0xe4e8df, .75); fill.position.set(center.x - 8, 5, center.z - 4); scene.add(fill)
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(width, depth), material(0xd4d6cf)); floor.rotation.x = -Math.PI / 2; floor.position.set(center.x, 0, center.z); floor.receiveShadow = true; floor.userData.kind = 'floor'; scene.add(floor)
    const grid = new THREE.GridHelper(Math.max(width, depth), 20, 0x899087, 0xb8bcb3); grid.position.set(center.x, .004, center.z); const gridMaterials = Array.isArray(grid.material) ? grid.material : [grid.material]; gridMaterials.forEach((item) => { item.transparent = true; item.opacity = .56 }); scene.add(grid)
    const whiteboxUrl = snapshot.room.whiteboxGlbUrl; let referenceSection: ReturnType<typeof createWallSectionIndex> | null = null; let wallCollisionBoxes: Array<{ wallId: string; bounds: THREE.Box3 }> = []; let fixtureCollisionBoxes: THREE.Box3[] = []
    if (whiteboxUrl) new GLTFLoader().load(whiteboxUrl, ({ scene: model }) => { if (disposed) return; model.name = 'floorplan_whitebox'; model.traverse((child) => { if (!(child instanceof THREE.Mesh)) return; const sources = Array.isArray(child.material) ? child.material : [child.material]; const materials = sources.map((source) => { const clone = source.clone(); clone.userData.sectionBaseOpacity = clone.opacity; clone.userData.sectionBaseTransparent = clone.transparent; clone.userData.sectionBaseDepthWrite = clone.depthWrite; return clone }); child.material = Array.isArray(child.material) ? materials : materials[0]; child.castShadow = true; child.receiveShadow = true }); scene.add(model); model.updateMatrixWorld(true); referenceSection = createWallSectionIndex(model); wallCollisionBoxes = referenceSection.wallMeshes.flatMap((mesh) => { const wallId = referenceSection?.meshToWallId.get(mesh); return wallId ? [{ wallId, bounds: new THREE.Box3().setFromObject(mesh) }] : [] }); fixtureCollisionBoxes = [...new Set([...referenceSection.groups.values()].flatMap((group) => group.fixtureMeshes))].map((mesh) => new THREE.Box3().setFromObject(mesh)) }, undefined, () => undefined)
    let whiteboxAligned = false
    const objectRoots = new Map<string, THREE.Group>(); const loader = new GLTFLoader()
    objectRootsRef.current = objectRoots
    snapshot.objects.forEach((item) => {
      const wrapper = new THREE.Group(); wrapper.userData = { kind: 'furniture', id: item.instanceId }; wrapper.name = item.instanceId; wrapper.position.fromArray(item.transform.position); wrapper.rotation.fromArray(item.transform.rotation); wrapper.scale.fromArray(item.transform.scale); scene.add(wrapper); objectRoots.set(item.instanceId, wrapper)
      if (item.geometry.glbUrl) loader.load(item.geometry.glbUrl, ({ scene: model }) => { if (disposed) return; try { normalizeModel(model, item.geometry.size); wrapper.add(model) } catch { wrapper.add(fallbackObject(item)) } }, undefined, () => { if (!disposed) wrapper.add(fallbackObject(item)) })
      else wrapper.add(fallbackObject(item))
    })
    const outline = new THREE.Box3Helper(new THREE.Box3(), 0xd9ed63); scene.add(outline); outline.visible = false
    const view = new THREE.Vector3(); let sectioned: string | null = null; let sectionFade = 0
    const raycaster = new THREE.Raycaster(); const pointer = new THREE.Vector2(); let dragging: { id: string; offset: THREE.Vector3; moved: boolean; result: PlacementResult } | null = null
    const pointerNdc = (event: PointerEvent) => { const rect = renderer.domElement.getBoundingClientRect(); pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1) }
    const rootData = (object: THREE.Object3D | null): { kind?: string; id?: string } => { let current = object; while (current) { if (current.userData.kind) return current.userData as { kind?: string; id?: string }; current = current.parent } return {} }
    const onDown = (event: PointerEvent) => { pointerNdc(event); raycaster.setFromCamera(pointer, camera); const hit = raycaster.intersectObjects([...objectRoots.values()], true)[0]; if (!hit) { onSelectRef.current(''); return } const data = rootData(hit.object); if (!data.id) return; onSelectRef.current(data.id); const root = objectRoots.get(data.id); const item = snapshotRef.current.objects.find((entry) => entry.instanceId === data.id); if (!root || !item) return; dragging = { id: data.id, offset: root.position.clone().sub(hit.point), moved: false, result: { position: [...item.transform.position], rotation: [...item.transform.rotation], surface: item.placement.surface ?? 'floor', supportObjectId: item.placement.supportObjectId ?? null, wallId: null } }; controls.enabled = false; renderer.domElement.setPointerCapture(event.pointerId)
    }
    const onMove = (event: PointerEvent) => { if (!dragging) return; pointerNdc(event); raycaster.setFromCamera(pointer, camera)
      const root = objectRoots.get(dragging.id); if (!root) return; const currentSnapshot = snapshotRef.current; const item = currentSnapshot.objects.find((entry) => entry.instanceId === dragging?.id); if (!item) return
      const surfaces: Array<{ kind: SurfaceKind; hit: THREE.Intersection<THREE.Object3D>; supportObjectId: string | null; wallId: string | null }> = []
      const floorHit = raycaster.intersectObject(floor, false)[0]; if (floorHit) surfaces.push({ kind: 'floor', hit: floorHit, supportObjectId: null, wallId: null })
      objectRoots.forEach((supportRoot, supportId) => { if (supportId === dragging?.id) return; const supportHit = raycaster.intersectObject(supportRoot, true).find((hit) => (worldNormal(hit)?.y ?? 0) > .55); if (supportHit) surfaces.push({ kind: 'object', hit: supportHit, supportObjectId: supportId, wallId: null }) })
      const section = referenceSection; if (section) { const wallHit = raycaster.intersectObjects(section.wallMeshes, false).find((hit) => { const normal = worldNormal(hit); const wallId = section.meshToWallId.get(hit.object); return !!normal && Math.abs(normal.y) < .6 && wallId !== sectioned }); const wallId = wallHit ? section.meshToWallId.get(wallHit.object) : null; if (wallHit && wallId) surfaces.push({ kind: 'wall', hit: wallHit, supportObjectId: null, wallId }) }
      const prefersWall = item.placement.surface === 'wall'
      const surfacePriority = (kind: SurfaceKind) => kind === 'object' ? 0 : kind === (prefersWall ? 'wall' : 'floor') ? 1 : 2
      surfaces.sort((left, right) => surfacePriority(left.kind) - surfacePriority(right.kind) || left.hit.distance - right.hit.distance)
      let accepted: PlacementResult | null = null
      for (const surface of surfaces) {
        const rotation: Vector3 = [...item.transform.rotation]; let position: Vector3
        const scaledHeight = item.geometry.size[1] * item.transform.scale[1]; const halfHeight = scaledHeight / 2
        if (surface.kind === 'wall') {
          const normal = worldNormal(surface.hit); if (!normal) continue; const towardRoom = center.clone().sub(surface.hit.point).setY(0); if (normal.dot(towardRoom) < 0) normal.negate()
          rotation[1] = Math.atan2(normal.x, normal.z)
          const halfDepth = item.geometry.size[2] * item.transform.scale[2] / 2
          const wallBounds = new THREE.Box3().setFromObject(surface.hit.object); const minY = wallBounds.min.y + halfHeight; const maxY = wallBounds.max.y - halfHeight
          const centerY = minY <= maxY ? Math.max(minY, Math.min(maxY, surface.hit.point.y)) : (wallBounds.min.y + wallBounds.max.y) / 2
          position = [surface.hit.point.x + normal.x * (halfDepth + .01), centerY, surface.hit.point.z + normal.z * (halfDepth + .01)]
        } else if (surface.kind === 'object' && surface.supportObjectId) {
          const support = currentSnapshot.objects.find((entry) => entry.instanceId === surface.supportObjectId); if (!support) continue
          const supportBounds = objectBounds(support); const candidateSize = objectBounds(item, [0, 0, 0], rotation).getSize(new THREE.Vector3()); const halfX = candidateSize.x / 2; const halfZ = candidateSize.z / 2
          if (candidateSize.x > supportBounds.max.x - supportBounds.min.x + .01 || candidateSize.z > supportBounds.max.z - supportBounds.min.z + .01) continue
          const targetX = surface.hit.point.x + dragging.offset.x; const targetZ = surface.hit.point.z + dragging.offset.z
          position = [Math.max(supportBounds.min.x + halfX, Math.min(supportBounds.max.x - halfX, targetX)), supportBounds.max.y + halfHeight + .005, Math.max(supportBounds.min.z + halfZ, Math.min(supportBounds.max.z - halfZ, targetZ))]
        } else {
          const candidateSize = objectBounds(item, [0, 0, 0], rotation).getSize(new THREE.Vector3()); const halfX = candidateSize.x / 2; const halfZ = candidateSize.z / 2
          position = [Math.round(Math.max(b.minX + halfX, Math.min(b.maxX - halfX, surface.hit.point.x + dragging.offset.x)) * 10) / 10, halfHeight, Math.round(Math.max(b.minZ + halfZ, Math.min(b.maxZ - halfZ, surface.hit.point.z + dragging.offset.z)) * 10) / 10]
        }
        const candidateBounds = objectBounds(item, position, rotation); const collidesWithObject = currentSnapshot.objects.some((other) => other.instanceId !== item.instanceId && other.instanceId !== surface.supportObjectId && overlaps(candidateBounds, objectBounds(other)))
        if (!collidesWithObject) { accepted = { position, rotation, surface: surface.kind, supportObjectId: surface.supportObjectId, wallId: surface.wallId }; break }
      }
      if (!accepted) return
      if (accepted.position.some((value, index) => Math.abs(value - root.position.toArray()[index]) > 1e-6) || Math.abs(accepted.rotation[1] - root.rotation.y) > 1e-6) dragging.moved = true
      dragging.result = accepted; root.position.fromArray(accepted.position); root.rotation.fromArray(accepted.rotation); root.updateMatrixWorld(true)
    }
    const onUp = (event: PointerEvent) => { if (!dragging) return; rememberCamera(); if (dragging.moved) objectRef.current(dragging.id, { position: dragging.result.position, rotation: dragging.result.rotation }, { surface: dragging.result.surface, supportObjectId: dragging.result.supportObjectId }); dragging = null; controls.enabled = true; if (renderer.domElement.hasPointerCapture(event.pointerId)) renderer.domElement.releasePointerCapture(event.pointerId) }
    renderer.domElement.addEventListener('pointerdown', onDown); renderer.domElement.addEventListener('pointermove', onMove); renderer.domElement.addEventListener('pointerup', onUp); renderer.domElement.addEventListener('pointercancel', onUp)
    const resize = () => { const widthPx = host.clientWidth; const heightPx = host.clientHeight; renderer.setSize(widthPx, heightPx, false); camera.aspect = widthPx / Math.max(heightPx, 1); camera.updateProjectionMatrix() }; const observer = new ResizeObserver(resize); observer.observe(host); resize()
    const animate = () => { animation = requestAnimationFrame(animate); controls.update(); const activeId = selectedRef.current; const selected = objectRoots.get(activeId); if (selected) { outline.box.setFromObject(selected); outline.visible = true; const intersectsStructure = wallCollisionBoxes.some((wall) => overlaps(outline.box, wall.bounds, .01)) || fixtureCollisionBoxes.some((fixture) => overlaps(outline.box, fixture, .01)); (outline.material as THREE.LineBasicMaterial).color.setHex(intersectsStructure ? 0xd64040 : 0xd9ed63) } else outline.visible = false
      const section = referenceSection
      if (section && !whiteboxAligned) {
        const model = scene.getObjectByName('floorplan_whitebox')
        if (model) {
          const modelBounds = new THREE.Box3().setFromObject(model)
          const modelCenter = modelBounds.getCenter(new THREE.Vector3())
          model.position.x += center.x - modelCenter.x
          model.position.z += center.z - modelCenter.z
          model.position.y -= modelBounds.min.y
          model.updateMatrixWorld(true)
          wallCollisionBoxes = section.wallMeshes.flatMap((mesh) => {
            const wallId = section.meshToWallId.get(mesh)
            return wallId ? [{ wallId, bounds: new THREE.Box3().setFromObject(mesh) }] : []
          })
          fixtureCollisionBoxes = [...new Set([...section.groups.values()].flatMap((group) => group.fixtureMeshes))].map((mesh) => new THREE.Box3().setFromObject(mesh))
          whiteboxAligned = true
        }
      }
      if (section) {
        const hits = AUTO_SECTION_RAY_SAMPLES.flatMap((sample) => { raycaster.setFromCamera(sample, camera); const hit = raycaster.intersectObjects(section.wallMeshes, false)[0]; const wallId = hit ? section.meshToWallId.get(hit.object) : undefined; return wallId && hit ? [{ wallId, distance: hit.distance }] : [] })
        camera.getWorldDirection(view)
        const selectedWall = selectFrontmostSectionWall({ hits, groups: section.groups, viewDirectionXZ: new THREE.Vector2(view.x, view.z), polarAngle: controls.getPolarAngle(), cameraTargetDistance: camera.position.distanceTo(controls.target), currentWallId: sectioned })
        sectionFade = selectedWall ? THREE.MathUtils.smoothstep(selectedWall.incidence, .82, .96) : 0
        sectioned = sectionFade > 0 ? selectedWall?.wallId ?? null : null
        section.groups.forEach((group, id) => [...group.wallMeshes, ...group.fixtureMeshes].forEach((mesh) => {
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
          materials.forEach((mat) => {
            const baseOpacity = typeof mat.userData.sectionBaseOpacity === 'number' ? mat.userData.sectionBaseOpacity as number : 1
            const fade = id === sectioned ? sectionFade : 0; const targetOpacity = baseOpacity * (1 - fade); const nextOpacity = mat.opacity + (targetOpacity - mat.opacity) * .16
            mat.opacity = Math.abs(nextOpacity - targetOpacity) < .008 ? targetOpacity : nextOpacity
            const baseTransparent = mat.userData.sectionBaseTransparent === true; const transparent = baseTransparent || mat.opacity < .999
            if (mat.transparent !== transparent) { mat.transparent = transparent; mat.needsUpdate = true }
            mat.depthWrite = fade > .55 ? false : mat.userData.sectionBaseDepthWrite !== false
          })
        }))
      } else { sectioned = null; sectionFade = 0 }
      renderer.render(scene, camera) }
    animate()
    return () => { disposed = true; if (objectRootsRef.current === objectRoots) objectRootsRef.current = new Map(); rememberCamera(); cancelAnimationFrame(animation); observer.disconnect(); renderer.domElement.removeEventListener('pointerdown', onDown); renderer.domElement.removeEventListener('pointermove', onMove); renderer.domElement.removeEventListener('pointerup', onUp); renderer.domElement.removeEventListener('pointercancel', onUp); controls.removeEventListener('change', rememberCamera); controls.dispose(); renderer.dispose(); scene.traverse((object) => { if (object instanceof THREE.Mesh) { object.geometry.dispose(); const mats = Array.isArray(object.material) ? object.material : [object.material]; mats.forEach((m) => m.dispose()) } }); renderer.domElement.remove() }
  }, [roomKey, structureKey])
  return <div className='scene-editor-canvas' ref={hostRef} data-testid='scene-canvas' />
}
