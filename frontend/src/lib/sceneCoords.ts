/** Layout coords: room corner (0,0) on XZ. Viewer: room center at origin. */

export interface RoomExtents {
  width: number
  depth: number
}

export function layoutToViewer(
  layout: [number, number, number],
  room: RoomExtents,
): [number, number, number] {
  return [layout[0] - room.width / 2, layout[1], layout[2] - room.depth / 2]
}

export function viewerToLayout(
  viewer: [number, number, number],
  room: RoomExtents,
): [number, number, number] {
  return [viewer[0] + room.width / 2, viewer[1], viewer[2] + room.depth / 2]
}
