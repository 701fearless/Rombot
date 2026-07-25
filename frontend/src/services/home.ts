// ============================================================
// 房屋/房间/摆放服务（本轮返回 Mock，签名即真实接口契约）
// ============================================================

import type { Home, ID, Placement, Room } from '@/types/models'
import { mockHomes, mockPlacements, mockRooms } from '@/mock'
import { mockDelay } from './delay'

/**
 * 获取用户的房屋列表
 * TODO: GET /api/v1/homes?userId=
 */
export function fetchHomes(userId: ID): Promise<Home[]> {
  return mockDelay(mockHomes.filter((h) => h.ownerId === userId))
}

/**
 * 获取某套房屋的房间列表
 * TODO: GET /api/v1/homes/{homeId}/rooms
 */
export function fetchRooms(homeId: ID): Promise<Room[]> {
  return mockDelay(mockRooms.filter((r) => r.homeId === homeId))
}

/**
 * 获取某房间的摆放列表
 * TODO: GET /api/v1/rooms/{roomId}/placements
 */
export function fetchPlacements(roomId: ID): Promise<Placement[]> {
  return mockDelay(mockPlacements.filter((p) => p.roomId === roomId))
}
