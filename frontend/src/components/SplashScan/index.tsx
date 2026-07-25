// SplashScan：开屏动画（每次启动只播一次）
// 视觉复用 HeroScan（油画底图 + 监控检测框扫描），播完停留片刻后整层淡出，
// 淡出结束通知父级卸载，露出下方的功能页；点击任意处可跳过
import { Text, View } from '@tarojs/components'
import { useEffect, useRef, useState } from 'react'
import HeroScan from '../HeroScan'
import type { DetectedItem } from '../HeroScan'
import './index.scss'

const HOLD_MS = 3000 // 扫描/检测框入场播完后的停留时长
const FADE_MS = 600 // 淡出过渡时长（与 index.scss 中 transition 一致）

export interface SplashScanProps {
  imageUrl: string
  items: DetectedItem[]
  title?: string
  subtitle?: string
  /** 淡出结束后的回调（父级此时卸载开屏层） */
  onDone: () => void
}

export default function SplashScan({ imageUrl, items, title, subtitle, onDone }: SplashScanProps) {
  const [fading, setFading] = useState(false)
  const doneRef = useRef(false)

  const finish = () => {
    if (doneRef.current) return
    doneRef.current = true
    onDone()
  }

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFading(true), HOLD_MS)
    const doneTimer = setTimeout(finish, HOLD_MS + FADE_MS)
    return () => {
      clearTimeout(fadeTimer)
      clearTimeout(doneTimer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSkip = () => {
    if (fading) return
    setFading(true)
    setTimeout(finish, FADE_MS)
  }

  return (
    <View className={`splash-scan ${fading ? 'is-fading' : ''}`} onClick={handleSkip}>
      <HeroScan
        imageUrl={imageUrl}
        items={items}
        title={title}
        subtitle={subtitle}
        interactive={false}
      />
      <Text className='splash-scan__skip'>轻触跳过</Text>
    </View>
  )
}
