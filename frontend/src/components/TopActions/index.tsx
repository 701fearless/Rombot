import { Text, View } from '@tarojs/components'
import './index.scss'

export interface TopActionsProps {
  onInvite?: () => void
  onShare?: () => void
}

export default function TopActions({ onInvite, onShare }: TopActionsProps) {
  return (
    <View className='top-actions'>
      <View className='top-actions__btn' onClick={onInvite}>
        <Text className='top-actions__icon'>＋</Text>
        <Text className='top-actions__text'>共建</Text>
      </View>
      <View className='top-actions__btn' onClick={onShare}>
        <Text className='top-actions__icon'>↗</Text>
        <Text className='top-actions__text'>分享</Text>
      </View>
    </View>
  )
}
