import type { SceneSnapshot } from '@/types/scene'
const numberValue = (value: unknown, fallback = 0) => typeof value === 'number' && Number.isFinite(value) ? value : fallback
export function snapshotToSceneResponse(snapshot: SceneSnapshot): Record<string, unknown> {
  const xs = snapshot.room.floorPolygon.map(([x]) => x); const zs = snapshot.room.floorPolygon.map(([, z]) => z)
  const minX = Math.min(...xs); const maxX = Math.max(...xs); const minZ = Math.min(...zs); const maxZ = Math.max(...zs)
  return { sceneId: snapshot.sceneId, unit: snapshot.unit, room: { width: maxX - minX, depth: maxZ - minZ, height: Math.max(2.4, ...snapshot.room.walls.map((wall) => numberValue(wall.height, 0))) }, objects: snapshot.objects.map((item) => ({ id: item.instanceId, label: item.semantic.label, name: item.semantic.name, position: item.transform.position, rotation: item.transform.rotation, size: item.geometry.effectiveSize ?? item.geometry.size.map((value, index) => value * item.transform.scale[index]), glbUrl: item.geometry.glbUrl ?? null })), openings: [], suggestions: [] }
}
