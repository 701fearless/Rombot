// HeroScan：AI 家具检测框 Hero
// 「计算机视觉目标检测」风格：古典油画底图 + 监控检测框 + 匹配度标签
// 入场：扫描线自上而下扫过，检测框按 y 排序依次描边生长 + 标签打字机
// 常态：框透明度呼吸、标签数字偶发跳动；交互：hover/tap 展开迷你匹配卡
import { Image, Text, View } from '@tarojs/components'
import { useEffect, useMemo, useRef, useState } from 'react'
import { isTouchDevice } from '@/utils/haptics'
import './index.scss'

export interface DetectedItem {
  id: string
  label: string // 如 "ARMCHAIR_01"
  score: number // 0~1 匹配度
  rect: { x: number; y: number; w: number; h: number } // 占容器百分比 0~100
  targetFurnitureId?: string
}

export interface HeroScanProps {
  imageUrl: string
  items: DetectedItem[]
  title?: string
  subtitle?: string
  ctaText?: string
  /** false = 纯展示（开屏动画用），检测框不响应点击 */
  interactive?: boolean
  onCtaClick?: () => void
  onItemClick?: (item: DetectedItem) => void
}

// 入场序列时间参数（总时长约 2.5s，只播一次）
const SCAN_LINE_MS = 1400
const BOX_STAGGER_MS = 150

export default function HeroScan({
  imageUrl,
  items,
  title,
  subtitle,
  ctaText,
  interactive = true,
  onCtaClick,
  onItemClick,
}: HeroScanProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const [scanning, setScanning] = useState(true)
  const [activeId, setActiveId] = useState<string | null>(null)
  // 标签匹配度数字偶发末位跳动（低频，模拟实时识别）
  const [tick, setTick] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval>>()

  // 按 rect.y 排序：扫描线扫到之处依次出现
  const sortedItems = useMemo(() => [...items].sort((a, b) => a.rect.y - b.rect.y), [items])

  useEffect(() => {
    const total = SCAN_LINE_MS + sortedItems.length * BOX_STAGGER_MS + 400
    const done = setTimeout(() => setScanning(false), total)
    timerRef.current = setInterval(() => setTick((t) => t + 1), 2600)
    return () => {
      clearTimeout(done)
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [sortedItems.length])

  // 自动演示（P1-2，仅触摸端）：入场动画播完后，自动展开第一个检测框的匹配卡 1.6s，
  // 告诉用户「框可以点」；用户已手动交互则跳过不打扰
  const autoDemoFiredRef = useRef(false)
  useEffect(() => {
    if (!interactive || !isTouchDevice() || autoDemoFiredRef.current) return
    const first = sortedItems[0]
    if (!first) return
    autoDemoFiredRef.current = true
    const startDelay = SCAN_LINE_MS + sortedItems.length * BOX_STAGGER_MS + 800
    const t1 = setTimeout(
      () => setActiveId((cur) => cur ?? first.id),
      startDelay,
    )
    const t2 = setTimeout(
      () => setActiveId((cur) => (cur === first.id ? null : cur)),
      startDelay + 1600,
    )
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interactive, sortedItems.length])

  // 每个框的入场延迟：扫描线先到（按 y 线性映射），再 stagger
  const delayOf = (item: DetectedItem, index: number) =>
    (item.rect.y / 100) * SCAN_LINE_MS + index * BOX_STAGGER_MS

  // 标签文本：匹配度保留 3 位；tick 偶发让末位 ±1 跳动
  const labelOf = (item: DetectedItem, index: number) => {
    let score = item.score
    if ((tick + index) % 7 === 0) {
      score = Math.min(0.999, Math.max(0.001, score + (tick % 2 === 0 ? 0.001 : -0.001)))
    }
    return `${item.label} · ${score.toFixed(3)}`
  }

  const handleItemClick = (item: DetectedItem) => {
    setActiveId((cur) => (cur === item.id ? null : item.id))
  }

  return (
    <View className='hero-scan'>
      <View className='hero-scan__stage'>
        {/* 底图：加载失败/为空时浮雕兜底，禁白屏（PRD 第 7 节） */}
        {!imgFailed && imageUrl ? (
          <Image
            className='hero-scan__img'
            src={imageUrl}
            mode='aspectFill'
            onError={() => setImgFailed(true)}
          />
        ) : (
          <View className='hero-scan__img-fallback'>
            <Text className='hero-scan__img-fallback-text'>空间影像加载中</Text>
          </View>
        )}

        {/* 扫描线（仅入场期间渲染） */}
        {scanning && <View className='hero-scan__scanline' />}

        {/* 检测框层：压暗时非激活框透明度降低 */}
        {sortedItems.map((item, i) => {
          const active = activeId === item.id
          const dimmed = activeId !== null && !active
          return (
            <View
              key={item.id}
              className={`hero-scan__box ${active ? 'is-active' : ''} ${dimmed ? 'is-dimmed' : ''}`}
              style={{
                left: `${item.rect.x}%`,
                top: `${item.rect.y}%`,
                width: `${item.rect.w}%`,
                height: `${item.rect.h}%`,
                animationDelay: `${delayOf(item, i)}ms`,
              }}
              onClick={interactive ? () => handleItemClick(item) : undefined}
            >
              {/* 四角刻度标记 */}
              <View className='hero-scan__corner hero-scan__corner--tl' />
              <View className='hero-scan__corner hero-scan__corner--tr' />
              <View className='hero-scan__corner hero-scan__corner--bl' />
              <View className='hero-scan__corner hero-scan__corner--br' />

              {/* 标签：等宽字体，扫描完成后打字机式出现 */}
              <View
                className='hero-scan__tag'
                style={{ animationDelay: `${delayOf(item, i) + 300}ms` }}
              >
                <Text className='hero-scan__tag-text'>{labelOf(item, i)}</Text>
              </View>

              {/* 激活时展开迷你匹配卡 */}
              {active && (
                <View className='hero-scan__card liquid-glass'>
                  <Text className='hero-scan__card-label'>{item.label}</Text>
                  <Text className='hero-scan__card-score'>
                    匹配 {Math.round(item.score * 100)}%
                  </Text>
                  <View
                    className='hero-scan__card-btn'
                    onClick={(e) => {
                      e.stopPropagation?.()
                      onItemClick?.(item)
                    }}
                  >
                    <Text className='hero-scan__card-btn-text'>查看匹配</Text>
                  </View>
                </View>
              )}
            </View>
          )
        })}

        {/* 文案层：PRD 2.4② 递进入场（0 / .2s / .4s） */}
        <View className={`hero-scan__copy ${activeId !== null ? 'is-dimmed' : ''}`}>
          {title && <Text className='hero-scan__title animate-fade-rise'>{title}</Text>}
          {subtitle && (
            <Text className='hero-scan__subtitle animate-fade-rise-delay'>{subtitle}</Text>
          )}
          {ctaText && (
            <View className='hero-scan__cta animate-fade-rise-delay-2' onClick={onCtaClick}>
              <Text className='hero-scan__cta-text'>{ctaText}</Text>
            </View>
          )}
        </View>
      </View>
    </View>
  )
}
