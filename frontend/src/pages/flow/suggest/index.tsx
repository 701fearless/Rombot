// AI 建议流：通用建议（兜底，永不空）→ 场景化建议（点开才采画像）
// 埋点：点开「风水」类建议 → logSignal('view_fengshui')（PRD 第 6 节）
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useCallback, useEffect, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import EmbossCard from '@/components/EmbossCard'
import type { SuggestionItem } from '@/mock'
import { fetchSuggestions } from '@/services/ai'
import { logSignal } from '@/utils/signal'
import './index.scss'

export default function SuggestPage() {
  const { params } = useRouter()
  const [list, setList] = useState<SuggestionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [sceneMode, setSceneMode] = useState(false)

  const load = useCallback(
    async (scene: boolean) => {
      setLoading(true)
      try {
        const items = await fetchSuggestions(params.roomId ?? '', scene)
        setList(items)
      } catch {
        // 兜底：加载失败也不出空白页（PRD 5.1 兜底精神）
        setList([
          {
            id: 'sg_fallback',
            roomType: '通用',
            title: '通用空间建议',
            content: '大件家具先定位，再用灯光与软装做层次；拿不准时保持同色系。',
          },
        ])
      }
      setLoading(false)
    },
    [params.roomId],
  )

  useEffect(() => {
    load(false)
  }, [load])

  const handleSceneMode = () => {
    setSceneMode(true)
    load(true)
  }

  const handleOpen = (item: SuggestionItem) => {
    // 埋点：点开风水类建议
    if (item.sceneTag === 'fengshui') {
      logSignal('view_fengshui', { suggestionId: item.id, roomId: params.roomId })
    }
  }

  return (
    <View className='suggest'>
      <AppHeader title='QQ House' />
      <View className='suggest__header'>
        <Text className='suggest__title'>
          {sceneMode ? '场景化建议' : '通用空间建议'}
        </Text>
        <Text className='suggest__subtitle'>
          {sceneMode ? '已结合你的行为画像生成' : '不采集任何信息，人人适用'}
        </Text>
      </View>

      {!sceneMode && (
        <View className='suggest__upgrade emboss' onClick={handleSceneMode}>
          <Text className='suggest__upgrade-text'>获取场景化建议（将基于你的行为画像）→</Text>
        </View>
      )}

      {loading ? (
        // 骨架屏，禁白屏
        <View className='suggest__list'>
          {Array.from({ length: 3 }).map((_, i) => (
            <View key={i} className='suggest__skel emboss' />
          ))}
        </View>
      ) : (
        <View className='suggest__list'>
          {list.map((item) => (
            <EmbossCard key={item.id} className='suggest__card' onClick={() => handleOpen(item)}>
              <View className='suggest__card-head'>
                <Text className='suggest__card-title'>{item.title}</Text>
                <Text className='suggest__card-room'>{item.roomType}</Text>
              </View>
              <Text className='suggest__card-content'>{item.content}</Text>
              <View
                className='suggest__card-cta'
                onClick={() =>
                  Taro.navigateTo({ url: `/pages/flow/place/index?roomId=${params.roomId}` })
                }
              >
                <Text className='suggest__card-cta-text'>去摆放</Text>
              </View>
            </EmbossCard>
          ))}
        </View>
      )}
    </View>
  )
}
