// 四端口 Hero 区（Mainframe 风格）：扫描大卡 + 平面图/模板空间两小卡 + 抖音链接识别大卡（图片底）
// 大卡视频交互（P0-2）：
//  - PC：window 级 mousemove → 视频 scrub（delta → currentTime），行为不变
//  - 触摸设备：muted + autoplay + loop 自动播放；手指在大卡上「横向滑动」接管 scrub，
//    松手 2s 后恢复自动播放（配合 scss touch-action: pan-y，竖向滚动完全不受影响）
// 注意：scrub 监听必须走原生 addEventListener —— Taro View 不会转发 onMouseMove
import { Text, View } from '@tarojs/components'
import { useEffect, useRef } from 'react'
import { useTypewriter } from '@/hooks/useTypewriter'
// 抖音端口底图：AI 生成油画客厅（import 引用才会被 webpack 打包进 dist）
import douyinEntryImg from '@/assets/douyin-entry.png'
import heroRoomImg from '@/assets/hero-room.jpg'
import './index.scss'

// 视频（webpack 不处理 mp4，经 copy 到 dist 后按运行路径引用；hash 路由下基于根解析）
const OIL_ROOM_VIDEO = 'assets/video/oil-room.mp4'

export interface EntryHeroProps {
  onScan: () => void
  onFloorplan: () => void
  onTemplate: () => void
  onDouyin: () => void
  compact?: boolean
}

// PC 鼠标 scrub 灵敏度（Mainframe prompt：SENSITIVITY = 0.8）
const SCRUB_SENSITIVITY = 0.8
// 触摸 scrub 灵敏度：一次全屏宽横滑 ≈ 1.6 倍片长
const TOUCH_SCRUB_SENSITIVITY = 1.6
// 触摸接管触发阈值（px）：低于此视为轻点，不影响自动播放/点击跳转
const TOUCH_SCRUB_THRESHOLD = 12
// 松手后恢复自动播放的延迟（ms）
const RESUME_AUTOPLAY_DELAY = 2000

// 触摸设备判定（hover: none = 手机/平板触摸端）
const isTouchDevice = () =>
  typeof window !== 'undefined' &&
  typeof window.matchMedia === 'function' &&
  window.matchMedia('(hover: none)').matches

export default function EntryHero({
  onScan,
  onFloorplan,
  onTemplate,
  onDouyin,
  compact = false,
}: EntryHeroProps) {
  const prevXRef = useRef(0)
  const targetTimeRef = useRef(0)
  const seekingRef = useRef(false)
  const videoElRef = useRef<HTMLVideoElement | null>(null)
  const resumeTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const touchMode = isTouchDevice()

  useEffect(() => {
    // seek 完成后若目标已前移则继续追（队列化防 seek-flooding），否则解除占用
    const handleSeeked = () => {
      const v = videoElRef.current
      if (!v) return
      if (Math.abs(v.currentTime - targetTimeRef.current) > 0.05) {
        v.currentTime = targetTimeRef.current
      } else {
        seekingRef.current = false
      }
    }

    // 延迟解析 video：Taro 挂载时序不确定，mount 时元素可能还没插入 DOM，
    // 所以在每次事件触发时按需取（取到后缓存），彻底规避时序问题
    const resolveVideo = (): HTMLVideoElement | null => {
      if (videoElRef.current && document.contains(videoElRef.current)) {
        return videoElRef.current
      }
      const v = document.getElementById('entry-hero-scan-video') as HTMLVideoElement | null
      if (v) {
        videoElRef.current = v
        v.addEventListener('seeked', handleSeeked)
      }
      return v
    }

    // 统一 scrub 入口：把目标进度前推 offset 秒，空闲时立即 seek
    const scrubBy = (offsetSeconds: number) => {
      const v = resolveVideo()
      if (!v || !v.duration) return
      targetTimeRef.current = Math.max(
        0,
        Math.min(v.duration, targetTimeRef.current + offsetSeconds),
      )
      if (!seekingRef.current) {
        seekingRef.current = true
        v.currentTime = targetTimeRef.current
      }
    }

    // ---------- 触摸端：自动播放 + 卡片级横向触摸接管 ----------
    if (touchMode) {
      const v = resolveVideo()
      if (v) {
        // React 的 muted 只设 property 不可靠，手动兜底，保证 autoplay 生效
        v.muted = true
        v.defaultMuted = true
        v.play().catch(() => {})
      }

      let startX = 0
      let lastX = 0
      let scrubbing = false

      const onTouchStart = (e: TouchEvent) => {
        if (e.touches.length === 0) return
        startX = lastX = e.touches[0].clientX
        scrubbing = false
      }
      const onTouchMove = (e: TouchEvent) => {
        if (e.touches.length === 0) return
        const x = e.touches[0].clientX
        const delta = x - lastX
        lastX = x
        const video = resolveVideo()
        if (!video || !video.duration) return
        if (!scrubbing && Math.abs(x - startX) > TOUCH_SCRUB_THRESHOLD) {
          // 进入接管：暂停自动播放，目标进度对齐当前帧，避免跳变
          scrubbing = true
          video.pause()
          targetTimeRef.current = video.currentTime
          if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current)
        }
        if (scrubbing) {
          scrubBy((delta / window.innerWidth) * TOUCH_SCRUB_SENSITIVITY * video.duration)
        }
      }
      const onTouchEnd = () => {
        if (!scrubbing) return
        scrubbing = false
        // 松手 2s 无操作 → 恢复自动播放
        resumeTimerRef.current = setTimeout(() => {
          videoElRef.current?.play().catch(() => {})
        }, RESUME_AUTOPLAY_DELAY)
      }

      // 监听挂在大卡上而非 window：竖向滚动页面时不会误触 scrub
      const card = document.getElementById('entry-hero-scan-card')
      card?.addEventListener('touchstart', onTouchStart, { passive: true })
      card?.addEventListener('touchmove', onTouchMove, { passive: true })
      card?.addEventListener('touchend', onTouchEnd, { passive: true })
      card?.addEventListener('touchcancel', onTouchEnd, { passive: true })
      return () => {
        card?.removeEventListener('touchstart', onTouchStart)
        card?.removeEventListener('touchmove', onTouchMove)
        card?.removeEventListener('touchend', onTouchEnd)
        card?.removeEventListener('touchcancel', onTouchEnd)
        if (resumeTimerRef.current) clearTimeout(resumeTimerRef.current)
        if (videoElRef.current) videoElRef.current.removeEventListener('seeked', handleSeeked)
      }
    }

    // ---------- PC 端：window 级 mousemove scrub（原行为） ----------
    const handleMove = (clientX: number) => {
      const delta = clientX - prevXRef.current
      prevXRef.current = clientX
      scrubBy((delta / window.innerWidth) * SCRUB_SENSITIVITY * (resolveVideo()?.duration ?? 0))
    }
    const onMouseMove = (e: MouseEvent) => handleMove(e.clientX)

    window.addEventListener('mousemove', onMouseMove)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      if (videoElRef.current) videoElRef.current.removeEventListener('seeked', handleSeeked)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const scanType = useTypewriter('拍一下房间，先把真实的家装进来。', 42, 500)
  const floorType = useTypewriter('已有户型图，从平面图直接建空间。', 42, 760)
  const tmplType = useTypewriter('先用相似模板，也能马上试摆。', 42, 940)
  const douyinType = useTypewriter('刷到心动家具？一张截图就能放进家。', 42, 820)
  const scanText = compact ? '拍一下房间，先把真实的家装进来。' : scanType.displayed
  const floorText = compact ? '已有户型图，从平面图直接建空间。' : floorType.displayed
  const tmplText = compact ? '先用相似模板，也能马上试摆。' : tmplType.displayed
  const douyinText = compact ? '刷到心动家具？一张截图就能放进家。' : douyinType.displayed

  return (
    <View className={`entry-hero ${compact ? 'entry-hero--compact' : ''}`}>
      {/* ---------- 扫描大卡（hero 级，视频 scrub） ---------- */}
      <View className="entry-hero__scan" id="entry-hero-scan-card" onClick={onScan}>
        <video
          id="entry-hero-scan-video"
          className="entry-hero__scan-video"
          src={OIL_ROOM_VIDEO}
          poster={heroRoomImg}
          muted
          playsInline
          preload="auto"
          autoPlay={touchMode}
          loop={touchMode}
          disablePictureInPicture
        />
        <View className="entry-hero__scan-veil" />

        <View className="entry-hero__content">
          <View className="entry-hero__type-wrap">
            <Text className="entry-hero__type">
              {scanText}
              {!compact && !scanType.done && <Text className="entry-hero__cursor" />}
            </Text>
          </View>
          <View className="entry-hero__pills">
            <View className="entry-hero__pill entry-hero__pill--solid" onClick={onScan}>
              <Text className="entry-hero__pill-text entry-hero__pill-text--solid">
                扫描我的房间
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* ---------- 两小卡：上传平面图 / 选择模板空间 ---------- */}
      <View className="entry-hero__row">
        <View className="entry-hero__mini" onClick={onFloorplan}>
          <View className="entry-hero__type-wrap entry-hero__type-wrap--mini">
            <Text className="entry-hero__type entry-hero__type--mini">
              {floorText}
              {!compact && !floorType.done && <Text className="entry-hero__cursor" />}
            </Text>
          </View>
          <View className="entry-hero__pills">
            <View className="entry-hero__pill entry-hero__pill--solid" onClick={onFloorplan}>
              <Text className="entry-hero__pill-text entry-hero__pill-text--solid">上传平面图</Text>
            </View>
          </View>
        </View>

        <View className="entry-hero__mini" onClick={onTemplate}>
          <View className="entry-hero__type-wrap entry-hero__type-wrap--mini">
            <Text className="entry-hero__type entry-hero__type--mini">
              {tmplText}
              {!compact && !tmplType.done && <Text className="entry-hero__cursor" />}
            </Text>
          </View>
          <View className="entry-hero__pills">
            <View className="entry-hero__pill entry-hero__pill--solid" onClick={onTemplate}>
              <Text className="entry-hero__pill-text entry-hero__pill-text--solid">
                使用模板空间
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* ---------- 抖音链接识别大卡（图片底，风格对齐扫描大卡） ---------- */}
      <View className="entry-hero__douyin" onClick={onDouyin}>
        <img className="entry-hero__douyin-img" src={douyinEntryImg} alt="" />
        <View className="entry-hero__scan-veil" />
        <View className="entry-hero__content">
          <View className="entry-hero__type-wrap entry-hero__type-wrap--mini">
            <Text className="entry-hero__type entry-hero__type--mini">
              {douyinText}
              {!compact && !douyinType.done && <Text className="entry-hero__cursor" />}
            </Text>
          </View>
          <View className="entry-hero__pills">
            <View className="entry-hero__pill entry-hero__pill--solid" onClick={onDouyin}>
              <Text className="entry-hero__pill-text entry-hero__pill-text--solid">
                粘贴链接建模
              </Text>
            </View>
          </View>
        </View>
      </View>
    </View>
  )
}
