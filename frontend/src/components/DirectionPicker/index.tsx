import { Text, View } from '@tarojs/components'
import './index.scss'

export interface DirectionPickerProps {
  value?: string
  onChange?: (direction: string) => void
}

// MVP 四方向（与场景详情页四场景一一对应）
const DIRECTIONS = ['养宠', '养娃', '风水', '动线']

export default function DirectionPicker({ value, onChange }: DirectionPickerProps) {
  return (
    <View className='direction-picker'>
      {DIRECTIONS.map((d) => (
        <View
          key={d}
          className={`direction-picker__pill ${value === d ? 'is-active' : ''}`}
          onClick={() => onChange?.(d)}
        >
          <Text className={`direction-picker__text ${value === d ? 'is-active' : ''}`}>{d}</Text>
        </View>
      ))}
    </View>
  )
}
