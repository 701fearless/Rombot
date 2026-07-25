// Tab3 发现（2026-07-25 改版：一页完成，不再越跳越深）
// 选定方向后同页顺序向下展开：① 给建议 → ② 推单品 → ③ 是否直接改；
// 下方「场景改造」四张 MVP 场景卡 → 场景详情页（场景页入口，不再是孤儿页）
import { Text, View } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { useEffect, useMemo, useState } from 'react'
import AppHeader from '@/components/AppHeader'
import CoverImage from '@/components/CoverImage'
import DirectionActions from '@/components/DirectionActions'
import DirectionPicker from '@/components/DirectionPicker'
import DouyinLinkSheet from '@/components/DouyinLinkSheet'
import SectionTitle from '@/components/SectionTitle'
import { mockFurniture, sceneSuggestions } from '@/mock'
import { fetchSceneList } from '@/services/scene'
import { useHomeStore } from '@/store'
import type { Scene } from '@/types/models'
import { logSignal } from '@/utils/signal'
import './index.scss'

// 方向 → 画像标签（sceneSuggestions.sceneTag）
const TAG_BY_DIRECTION: Record<string, string> = {
  养宠: 'pet',
  养娃: 'baby',
  风水: 'fengshui',
  动线: 'move',
}

// 方向一句话（与场景详情页四场景一一对应）
const DIRECTION_META: Record<string, string> = {
  养宠: '给毛孩子留活动区与专属收纳，动线避开食盆水碗',
  养娃: '圆角防护、视线通透，留出亲子活动与爬行空间',
  风水: '床位朝向、门窗对冲、财位留白一并调整',
  动线: '梳理行走路径，减少绕行与磕碰点',
}

// 方向 → 推荐单品（MVP：每方向两件，note 说清为什么推它）
const ITEMS_BY_DIRECTION: Record<string, Array<{ id: string; note: string }>> = {
  养宠: [
    { id: 'f_pet_01', note: '给毛孩子一个专属窝，不再上你的沙发' },
    { id: 'f_sofa_02', note: '亚麻耐磨面料，经得起爪子和掉毛' },
  ],
  养娃: [
    { id: 'f_babybed_01', note: '可拼接实木婴儿床，远离绳线电源' },
    { id: 'f_table_02', note: '圆角边几替换尖角茶几，少一份磕碰' },
  ],
  风水: [
    { id: 'f_bed_02', note: '软包床调对朝向，床头靠实墙' },
    { id: 'f_lamp_02', note: '暖光台灯助眠，替代直射顶灯' },
  ],
  动线: [
    { id: 'f_sofa_01', note: '沙发贴墙定位，把主通道让出来' },
    { id: 'f_lamp_01', note: '落地灯照亮转角，夜里不磕碰' },
  ],
}

export default function DirectionPage() {
  const { params } = useRouter()
  const { homes, rooms } = useHomeStore()
  const [direction, setDirection] = useState<string | null>(null)
  const [scenes, setScenes] = useState<Scene[]>([])
  // 「链接识别」粘贴浮层（拍板：不做真外跳抖音，统一粘贴链接 → 识别流）
  const [showDouyinSheet, setShowDouyinSheet] = useState(false)

  useEffect(() => {
    fetchSceneList().then(setScenes)
  }, [])

  // Tab 直开无参数：回落到首要家（isPrimary 优先，否则第一套）的第一个房间
  const fallbackHome = homes.find((h) => h.isPrimary) ?? homes[0]
  const homeId = params.homeId ?? fallbackHome?.id ?? ''
  const roomId = params.roomId ?? rooms.find((r) => r.homeId === fallbackHome?.id)?.id ?? ''

  // ① 建议：按方向画像标签过滤
  const suggestions = useMemo(
    () => sceneSuggestions.filter((s) => s.sceneTag === TAG_BY_DIRECTION[direction ?? '']),
    [direction],
  )
  // ② 单品：按方向取两件
  const items = useMemo(
    () =>
      (ITEMS_BY_DIRECTION[direction ?? ''] ?? [])
        .map(({ id, note }) => ({ furniture: mockFurniture.find((f) => f.id === id), note }))
        .filter((r) => !!r.furniture),
    [direction],
  )

  // ③ 直接改：带方向进摆放页（place 页带 direction 不再自动弹操作台浮窗）
  const handleDirectEdit = () =>
    Taro.navigateTo({
      url: `/pages/flow/place/index?homeId=${homeId}&roomId=${roomId}&direction=${direction}`,
    })
  const handleAdvice = () =>
    Taro.navigateTo({
      url: `/pages/flow/suggest/index?roomId=${roomId}&direction=${direction ?? ''}`,
    })
  const handleRecommend = () =>
    Taro.navigateTo({
      url: `/pages/flow/recommend/index?roomId=${roomId}&direction=${direction ?? ''}`,
    })

  return (
    <View className='direction'>
      <AppHeader title='QQ House' />
      <SectionTitle title='发现' subtitle='选一个方向，建议、单品、改造一次给齐' />

      <View className='direction__community'>
        <View className='direction__community-head'>
          <Text className='direction__community-title'>其他人的家</Text>
          <Text className='direction__community-sub'>看看大家怎么把房间改舒服</Text>
        </View>
        <View className='direction__community-grid'>
          {scenes.slice(0, 3).map((s) => (
            <View
              key={`community_${s.id}`}
              className='direction__community-card'
              onClick={() => Taro.navigateTo({ url: `/pages/discover/scene/index?id=${s.id}` })}
            >
              <CoverImage src={s.coverUrl} title={s.title} ratio='4 / 3' />
              <View className='direction__community-copy'>
                <Text className='direction__community-name'>{s.title}</Text>
                <Text className='direction__community-meta'>{s.direction} · 已试改</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      <DirectionPicker value={direction ?? undefined} onChange={setDirection} />

      {direction && (
        // key=direction：切换方向时重播三段展开动画
        <View key={direction} className='direction__flow'>
          <Text className='direction__meta'>{DIRECTION_META[direction]}</Text>

          <DirectionActions
            onRecommend={handleAdvice}
            onGenerate={handleRecommend}
            onDirectEdit={handleDirectEdit}
          />

          {/* ① 先给建议 */}
          <View className='direction__step animate-fade-rise'>
            <Text className='direction__step-title'>① 先给建议</Text>
            {suggestions.map((s) => (
              <View
                key={s.id}
                className='direction__advice emboss'
                onClick={() =>
                  s.sceneTag === 'fengshui' &&
                  logSignal('view_fengshui', { suggestionId: s.id, roomId })
                }
              >
                <Text className='direction__advice-title'>{s.title}</Text>
                <Text className='direction__advice-content'>{s.content}</Text>
              </View>
            ))}
          </View>

          {/* ② 再推单品 */}
          <View className='direction__step animate-fade-rise-delay'>
            <Text className='direction__step-title'>② 再推单品</Text>
            {items.map(({ furniture, note }) => (
              <View key={furniture!.id} className='direction__item emboss'>
                <CoverImage
                  src={furniture!.coverUrl}
                  title={furniture!.title}
                  ratio='1 / 1'
                  className='direction__item-thumb'
                />
                <View className='direction__item-body'>
                  <Text className='direction__item-title'>{furniture!.title}</Text>
                  <Text className='direction__item-note'>{note}</Text>
                  <View className='direction__item-actions'>
                    <View
                      className='direction__btn'
                      onClick={() => Taro.showToast({ title: '已放入空间（mock）', icon: 'none' })}
                    >
                      <Text className='direction__btn-text'>放进空间</Text>
                    </View>
                    <View
                      className='direction__btn direction__btn--primary'
                      onClick={() => setShowDouyinSheet(true)}
                    >
                      <Text className='direction__btn-text direction__btn-text--primary'>
                        链接识别
                      </Text>
                    </View>
                  </View>
                </View>
              </View>
            ))}
          </View>

          {/* ③ 要不要直接改 */}
          <View className='direction__step animate-fade-rise-delay-2'>
            <Text className='direction__step-title'>③ 要不要直接改？</Text>
            <View className='direction__edit-cta' onClick={handleDirectEdit}>
              <Text className='direction__edit-cta-text'>
                按「{direction}」直接改空间看效果 →
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* 场景改造：四个 MVP 场景 → 场景详情页 */}
      <View className='direction__scenes'>
        <Text className='direction__scenes-title'>场景改造</Text>
        <Text className='direction__scenes-sub'>结合具体场景的需求，整套思路给你</Text>
        <View className='direction__scene-grid'>
          {scenes.map((s) => (
            <View
              key={s.id}
              className='direction__scene-card emboss'
              onClick={() =>
                Taro.navigateTo({ url: `/pages/discover/scene/index?id=${s.id}` })
              }
            >
              <CoverImage src={s.coverUrl} title={s.title} ratio='4 / 3' />
              <View className='direction__scene-card-body'>
                <Text className='direction__scene-card-title'>{s.title}</Text>
                <Text className='direction__scene-card-desc'>
                  {DIRECTION_META[s.direction] ?? ''}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* 粘贴抖音链接识别浮层 */}
      {showDouyinSheet && <DouyinLinkSheet onClose={() => setShowDouyinSheet(false)} />}
    </View>
  )
}
