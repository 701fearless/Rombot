import { View } from '@tarojs/components'
import roomPreview from '@/assets/space-3d-living.png'
import './index.scss'

export type SpaceViewMode = 'render' | 'plan'

export interface SpaceCanvasProps {
  children?: React.ReactNode
  mode?: SpaceViewMode
}

export default function SpaceCanvas({ children, mode = 'render' }: SpaceCanvasProps) {
  return (
    <View
      className={`space-canvas is-${mode}`}
      style={mode === 'render' ? { backgroundImage: `url(${roomPreview})` } : undefined}
    >
      <View className='space-canvas__scrim' />
      {children}
    </View>
  )
}
