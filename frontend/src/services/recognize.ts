// ============================================================
// 识别流服务（双入口汇入：入口A 上传 / 入口B 带 sourceId）
// ============================================================

import type { ID } from '@/types/models'
import { fallbackTemplateFurnitureId, mockFurniture } from '@/mock'
import { mockDelay } from './delay'

export interface RecognizeResult {
  furnitureId: ID
  confidence: number // 0~1
}

// 置信度阈值：低于此值走兜底模板（PRD 5.1：永不空结果）
const CONFIDENCE_THRESHOLD = 0.6

// 模拟一次识别：随机命中 + 随机置信度，低置信度回落到兜底通用模板
function mockRecognize(furnitureId?: ID): RecognizeResult {
  const confidence = Math.round((0.3 + Math.random() * 0.69) * 100) / 100
  if (confidence < CONFIDENCE_THRESHOLD) {
    return { furnitureId: fallbackTemplateFurnitureId, confidence }
  }
  const hitId =
    furnitureId ?? mockFurniture[Math.floor(Math.random() * mockFurniture.length)].id
  return { furnitureId: hitId, confidence }
}

/**
 * 入口A：截图/相册上传识别
 * TODO: POST /api/v1/recognize（multipart 上传图片）
 */
export function recognizeByUpload(): Promise<RecognizeResult> {
  return mockDelay(mockRecognize())
}

/**
 * 入口B：抖音挂车/评论链接带 sourceId 跳转识别
 * TODO: POST /api/v1/recognize { sourceId }
 */
export function recognizeBySourceId(sourceId: string): Promise<RecognizeResult> {
  // mock：按 sourceId 字符哈希稳定命中一件家具，模拟"链接对应商品"
  const hash = Array.from(sourceId).reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  const hitId = mockFurniture[hash % mockFurniture.length].id
  return mockDelay(mockRecognize(hitId))
}
