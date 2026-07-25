import { Text, View } from '@tarojs/components'
import './index.scss'

export interface ParamPanelProps {
  active?: string
}

export default function ParamPanel({ active = '配色/收纳' }: ParamPanelProps) {
  return (
    <View className='param-panel liquid-glass'>
      <Text className='param-panel__title'>参数面板</Text>
      <Text className='param-panel__value'>{active}</Text>
      <Text className='param-panel__hint'>当前方向：先收纳再补层次，整体留白更舒服</Text>
    </View>
  )
}
