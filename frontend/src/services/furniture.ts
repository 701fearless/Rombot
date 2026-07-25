// ============================================================
// 家具 SKU 库服务（本轮返回 Mock，签名即真实接口契约）
// ============================================================

import type { Furniture, ID } from '@/types/models'
import { mockFurniture } from '@/mock'
import { mockDelay } from './delay'

/**
 * 获取家具列表，可按品类过滤（沙发/床/桌/椅/柜/灯/婴儿床/宠物家具...）
 * TODO: GET /api/v1/furniture?category=
 */
export function fetchFurnitureList(category?: string): Promise<Furniture[]> {
  const list = category ? mockFurniture.filter((f) => f.category === category) : mockFurniture
  return mockDelay(list)
}

/**
 * 按 id 获取家具详情
 * TODO: GET /api/v1/furniture/{id}
 */
export function fetchFurnitureById(id: ID): Promise<Furniture | undefined> {
  return mockDelay(mockFurniture.find((f) => f.id === id))
}
