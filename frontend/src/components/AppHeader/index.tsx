import { Text, View } from '@tarojs/components'
import type React from 'react'
import AppTabBar from '@/components/AppTabBar'
import './index.scss'

export interface AppHeaderProps {
  title: string
  subtitle?: string
  right?: React.ReactNode
}

export default function AppHeader({ title, subtitle, right }: AppHeaderProps) {
  return (
    <>
      <View className='app-header'>
        <View className='app-header__copy'>
          <Text className='app-header__title'>{title}</Text>
          {subtitle && <Text className='app-header__subtitle'>{subtitle}</Text>}
        </View>
        {right && <View className='app-header__right'>{right}</View>}
      </View>
      <AppTabBar />
    </>
  )
}
