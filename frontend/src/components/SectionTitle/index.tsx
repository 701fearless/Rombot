// 区块标题：衬线主标题 + 次要副标题 + 右侧插槽
import { Text, View } from '@tarojs/components'
import type React from 'react'
import './index.scss'

export interface SectionTitleProps {
  title: string
  subtitle?: string
  extra?: React.ReactNode
}

export default function SectionTitle({ title, subtitle, extra }: SectionTitleProps) {
  return (
    <View className='section-title'>
      <View className='section-title__texts'>
        <Text className='section-title__title'>{title}</Text>
        {subtitle && <Text className='section-title__subtitle'>{subtitle}</Text>}
      </View>
      {extra && <View className='section-title__extra'>{extra}</View>}
    </View>
  )
}
