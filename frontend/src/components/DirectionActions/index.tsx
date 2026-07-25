import { Text, View } from '@tarojs/components'
import './index.scss'

export interface DirectionActionsProps {
  onRecommend?: () => void
  onGenerate?: () => void
  onDirectEdit?: () => void
}

export default function DirectionActions({ onRecommend, onGenerate, onDirectEdit }: DirectionActionsProps) {
  return (
    <View className='direction-actions'>
      <View className='direction-actions__item' onClick={onRecommend}>
        <Text className='direction-actions__index'>01</Text>
        <Text className='direction-actions__label'>给建议</Text>
      </View>
      <View className='direction-actions__item' onClick={onGenerate}>
        <Text className='direction-actions__index'>02</Text>
        <Text className='direction-actions__label'>荐单品</Text>
      </View>
      <View className='direction-actions__item is-primary' onClick={onDirectEdit}>
        <Text className='direction-actions__index is-primary'>03</Text>
        <Text className='direction-actions__label is-primary'>直接改</Text>
      </View>
    </View>
  )
}
