import Taro from '@tarojs/taro'
import type { ProfileSignal } from '@/types/models'
import { genId } from './id'
import { mockUser } from '@/mock'

// 行为信号本地存储 key（PRD 第 6 节：本轮存本地 Storage，为画像推断攒数据）
const SIGNALS_KEY = 'profile_signals'

/**
 * 埋点写入一条 ProfileSignal。
 * 铁律：append-only，只 insert 不 update（PRD 4 设计意图 3）。
 * TODO: 接真实后端后改为上报 POST /api/v1/signals
 */
export function logSignal(type: string, context?: Record<string, unknown>): void {
  const signal: ProfileSignal = {
    id: genId('sig'),
    userId: mockUser.unionId,
    type,
    context,
    ts: Date.now(),
  }
  const signals = getSignals()
  signals.push(signal) // 只追加，永不修改历史记录
  try {
    Taro.setStorageSync(SIGNALS_KEY, signals)
  } catch (e) {
    // 埋点失败不阻塞主流程
    console.warn('[signal] 写入 Storage 失败', e)
  }
}

/** 读取全部行为信号（调试用） */
export function getSignals(): ProfileSignal[] {
  try {
    const raw: unknown = Taro.getStorageSync(SIGNALS_KEY)
    return Array.isArray(raw) ? (raw as ProfileSignal[]) : []
  } catch {
    return []
  }
}
