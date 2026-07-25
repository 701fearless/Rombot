// Reveal：滚动进入视口时的 fade-rise 包装（P1-3）
// H5 用 IntersectionObserver 触发；小程序端（自定义组件内选择器受限）降级为立即展示
// 入场只播一次；delay 用于列表 stagger
import { View } from '@tarojs/components'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { genId } from '@/utils/id'
import './index.scss'

export interface RevealProps {
  children: ReactNode
  className?: string
  /** 入场延迟 ms（列表 stagger 用） */
  delay?: number
  onClick?: () => void
}

export default function Reveal({ children, className = '', delay = 0, onClick }: RevealProps) {
  const [shown, setShown] = useState(false)
  const domId = useMemo(() => genId('reveal'), [])

  useEffect(() => {
    if (process.env.TARO_ENV !== 'h5') {
      // 小程序端降级：直接展示（页面滚动监听成本高，保底不白屏）
      setShown(true)
      return
    }
    const el = document.getElementById(domId)
    if (!el || typeof IntersectionObserver === 'undefined') {
      setShown(true)
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          setShown(true)
          io.disconnect()
        }
      },
      { threshold: 0.12 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [domId])

  return (
    <View
      id={domId}
      className={`reveal ${shown ? 'is-shown' : ''} ${className}`}
      style={{ transitionDelay: shown ? `${delay}ms` : '0ms' }}
      onClick={onClick}
    >
      {children}
    </View>
  )
}
