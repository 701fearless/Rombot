import { Text, View } from '@tarojs/components'
import './index.scss'

export interface ReviewCardProps {
  issueLabel?: string
  text?: string
  score?: number
  open?: boolean
  onToggle?: () => void
  onFix?: () => void
  onSearch?: () => void
}

const DEFAULT_TEXT = '主通道略窄，建议把边几向左移动 24cm，保留至少 80cm 通行宽度。'

export default function ReviewCard({
  issueLabel = '动线可优化',
  text = DEFAULT_TEXT,
  score = 86,
  open = true,
  onToggle,
  onFix,
  onSearch,
}: ReviewCardProps) {
  return (
    <View className='review-card liquid-glass'>
      <View className='review-card__head'>
        <View className='review-card__heading'>
          <Text className='review-card__eyebrow'>AI 空间审查</Text>
          <Text className='review-card__title'>{issueLabel}</Text>
        </View>
        <View className='review-card__score'>
          <Text className='review-card__score-value'>{score}</Text>
          <Text className='review-card__score-unit'>分</Text>
        </View>
      </View>

      {open && (
        <>
          <View className='review-card__issue'>
            <View className='review-card__dot' />
            <Text className='review-card__text'>{text}</Text>
          </View>
          <View className='review-card__actions'>
            <View className='review-card__button is-secondary' onClick={onSearch}>
              <Text className='review-card__button-text'>搜同款</Text>
            </View>
            <View className='review-card__button is-primary' onClick={onFix}>
              <Text className='review-card__button-text is-primary'>AI 帮改</Text>
            </View>
          </View>
        </>
      )}

      <View className='review-card__toggle' onClick={onToggle}>
        <Text className='review-card__toggle-text'>{open ? '收起审查' : '查看审查详情'}</Text>
      </View>
    </View>
  )
}
