// 封面图：骨架屏 → 懒加载渐入；src 为空/加载失败时浮雕占位（标题首字符）
// 硬要求（PRD 第 7 节）：任何异步区域禁止白屏
import { Image, Text, View } from '@tarojs/components'
import { useState } from 'react'
import './index.scss'

export interface CoverImageProps {
  src?: string
  title: string
  /** CSS aspect-ratio，如 '4 / 3'、'1 / 1'，默认方形 */
  ratio?: string
  className?: string
  placeholderColor?: string
}

export default function CoverImage({
  src,
  title,
  ratio = '1 / 1',
  className = '',
  placeholderColor,
}: CoverImageProps) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)

  const showPlaceholder = !src || failed
  const safeTitle = typeof title === 'string' ? title : ''
  // 占位符取标题首个有效字符，衬线大字强化法式气质
  const initial = Array.from(safeTitle.trim())[0] ?? '·'

  return (
    <View className={`cover-image ${className}`.trim()} style={{ aspectRatio: ratio }}>
      {/* 骨架屏：加载完成前常驻底层，杜绝白屏 */}
      {!loaded && !showPlaceholder && <View className='cover-image__skeleton' />}
      {showPlaceholder ? (
        <View
          className='cover-image__placeholder'
          style={placeholderColor ? { backgroundColor: placeholderColor } : undefined}
        >
          <Text className='cover-image__initial'>{initial}</Text>
        </View>
      ) : (
        <Image
          className={`cover-image__img ${loaded ? 'is-loaded' : ''}`}
          src={src!}
          mode='aspectFill'
          lazyLoad
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      )}
    </View>
  )
}
