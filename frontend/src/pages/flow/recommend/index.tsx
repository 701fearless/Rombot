import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useMemo } from 'react'
import AppHeader from '@/components/AppHeader'
import { mockFurniture } from '@/mock'
import './index.scss'

export default function RecommendPage() {
  const { params } = useRouter()

  const items = useMemo(() => mockFurniture.slice(0, 4), [])

  return (
    <View className='recommend'>
      <AppHeader title='QQ House' />
      <View className='recommend__header'>
        <Text className='recommend__title'>单品推荐</Text>
        <Text className='recommend__subtitle'>方向：{params.direction ?? '养宠'}</Text>
      </View>

      <View className='recommend__list'>
        {items.map((f) => (
          <View key={f.id} className='recommend__card emboss'>
            <View className='recommend__card-body'>
              <Text className='recommend__card-title'>{f.title}</Text>
              <Text className='recommend__card-desc'>根据当前方向为你匹配了同风格单品。</Text>
            </View>
            <View className='recommend__actions'>
              <View className='recommend__btn recommend__btn--ghost'>
                <Text className='recommend__btn-text'>放进空间</Text>
              </View>
              <View
                className='recommend__btn recommend__btn--primary'
                onClick={() => {
                  if (f.priceRefs[0]?.url) {
                    Taro.navigateTo({ url: `/pages/discover/detail/index?id=${f.id}` })
                  }
                }}
              >
                <Text className='recommend__btn-text'>直达抖音</Text>
              </View>
            </View>
          </View>
        ))}
      </View>
    </View>
  )
}
