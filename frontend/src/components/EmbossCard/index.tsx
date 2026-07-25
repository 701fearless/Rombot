// 浮雕卡片容器（PRD 2.1：柔和浮雕，一明一暗双向阴影，非重描边）
import { View } from '@tarojs/components'
import type React from 'react'

export interface EmbossCardProps {
  children: React.ReactNode
  className?: string
  /** true = 凹陷（已按下/输入区），false = 凸出（默认） */
  inset?: boolean
  onClick?: () => void
}

export default function EmbossCard({ children, className = '', inset, onClick }: EmbossCardProps) {
  const cls = `${inset ? 'emboss-inset' : 'emboss'} emboss-card ${className}`.trim()
  return (
    <View className={cls} onClick={onClick}>
      {children}
    </View>
  )
}
