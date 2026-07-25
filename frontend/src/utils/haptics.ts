// 触感反馈（P1-1）：小程序走 Taro.vibrateShort；H5 用 navigator.vibrate 渐进增强
// 不支持/被系统拒绝时静默跳过，绝不影响业务流程
import Taro from '@tarojs/taro'

type HapticType = 'light' | 'medium' | 'heavy'

const vibrate = (ms: number, type: HapticType) => {
  try {
    if (process.env.TARO_ENV === 'h5') {
      // iOS Safari 不支持 vibrate，调用不存在时静默
      navigator?.vibrate?.(ms)
      return
    }
    Taro.vibrateShort({ type, fail: () => {} })
  } catch {
    /* 不支持则静默 */
  }
}

/** 轻触：抽书、选中切换 */
export const hapticLight = () => vibrate(12, 'light')

/** 中触：吸附对齐、落位成功 */
export const hapticMedium = () => vibrate(25, 'medium')

// 触摸设备判定：小程序端天然触摸；H5 用 (hover: none) 媒体查询
export const isTouchDevice = () => {
  if (process.env.TARO_ENV !== 'h5') return true
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(hover: none)').matches
  )
}
