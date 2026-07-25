// ============================================================
// 场景/方案服务（本轮返回 Mock，签名即真实接口契约）
// ============================================================

import type { ID, Scene } from '@/types/models'
import { mockScenes } from '@/mock'
import { mockDelay } from './delay'

/**
 * 获取场景列表
 * TODO: GET /api/v1/scenes
 */
export function fetchSceneList(): Promise<Scene[]> {
  return mockDelay(mockScenes)
}

/**
 * 按 id 获取场景详情（含家具元素列表）
 * TODO: GET /api/v1/scenes/{id}
 */
export function fetchSceneById(id: ID): Promise<Scene | undefined> {
  return mockDelay(mockScenes.find((s) => s.id === id))
}
