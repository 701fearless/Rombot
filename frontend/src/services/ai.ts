// ============================================================
// AI 建议流 / 整屋补全流服务（本轮返回 Mock）
// ============================================================

import type { ID } from '@/types/models'
import type { SuggestionItem } from '@/mock'
import { genericSuggestions, mockFurniture, sceneSuggestions } from '@/mock'
import { mockDelay } from './delay'

/**
 * 获取房间 AI 建议列表。
 * sceneProfile=false → 通用空间建议（兜底，永不出空白页）；
 * sceneProfile=true  → 场景化建议（含"风水"类，命中画像标签时使用）。
 * TODO: GET /api/v1/rooms/{roomId}/suggestions?sceneProfile=
 */
export function fetchSuggestions(_roomId: ID, sceneProfile = false): Promise<SuggestionItem[]> {
  return mockDelay(sceneProfile ? sceneSuggestions : genericSuggestions)
}

/**
 * 整屋补全：以锚点资产为基准，返回一组推荐搭配的 furnitureId
 * TODO: POST /api/v1/rooms/{roomId}/complete { anchorAssetId }
 */
export function fetchCompleteRoom(_roomId: ID, _anchorAssetId: ID): Promise<ID[]> {
  // mock：从 SKU 库挑 4 件不同品类作为搭配推荐
  const picked: ID[] = []
  const seen = new Set<string>()
  for (const f of mockFurniture) {
    if (!seen.has(f.category)) {
      seen.add(f.category)
      picked.push(f.id)
    }
    if (picked.length >= 4) break
  }
  return mockDelay(picked)
}
