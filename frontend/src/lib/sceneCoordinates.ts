import type { SceneSnapshot } from '@/types/scene'

export interface CanvasPoint { x: number; y: number }

export function sceneBounds(snapshot: SceneSnapshot) {
  const xs = snapshot.room.floorPolygon.map(([x]) => x)
  const zs = snapshot.room.floorPolygon.map(([, z]) => z)
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minZ: Math.min(...zs), maxZ: Math.max(...zs) }
}

export function worldToCanvas(snapshot: SceneSnapshot, position: [number, number, number], width: number, height: number): CanvasPoint {
  const bounds = sceneBounds(snapshot)
  return {
    x: ((position[0] - bounds.minX) / (bounds.maxX - bounds.minX)) * width,
    y: height - ((position[2] - bounds.minZ) / (bounds.maxZ - bounds.minZ)) * height,
  }
}

export function canvasToWorld(snapshot: SceneSnapshot, point: CanvasPoint, objectHeight: number, width: number, height: number): [number, number, number] {
  const bounds = sceneBounds(snapshot)
  return [
    bounds.minX + (point.x / width) * (bounds.maxX - bounds.minX),
    objectHeight / 2,
    bounds.minZ + ((height - point.y) / height) * (bounds.maxZ - bounds.minZ),
  ]
}
