import Taro from '@tarojs/taro'
import type { StateStorage } from 'zustand/middleware'

// zustand persist 的 Taro Storage 适配器（PRD 铁律：store 产物持久化到 Storage，退出不丢）
export const taroStorage: StateStorage = {
  getItem: (name: string): string | null => {
    try {
      const value: unknown = Taro.getStorageSync(name)
      // 未命中时 Taro 返回空字符串，统一归为 null
      return typeof value === 'string' && value !== '' ? value : null
    } catch {
      return null
    }
  },
  setItem: (name: string, value: string): void => {
    Taro.setStorageSync(name, value)
  },
  removeItem: (name: string): void => {
    Taro.removeStorageSync(name)
  },
}
