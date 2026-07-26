import { AlertCircle, Bookmark, Heart, Home, Inbox, LoaderCircle, MessageCircle, Music2, Pause, Plus, Share2, UserRound, UsersRound, Volume2, VolumeX } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ProductRecognizeSheet } from '@/components/ProductRecognizeSheet'
import { useToast } from '@/components/ToastProvider'
import { feedVideos } from '@/data/feedVideos'
import { computeVideoDHash } from '@/lib/dhash'
import { containTagPosition } from '@/lib/geometry'
import { detectPausedFrame, searchFeedProducts } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { FeedVideo } from '@/types/feed'
import type { DetectResponse, DetectedObject } from '@/types/scene'
import type { ShopProduct } from '@/types/shop'

interface Size { width: number; height: number }
interface FeedTagLayout { object: DetectedObject; left: number; top: number; direction: 'left' | 'right'; extent: number }

function canSearchProducts(object: DetectedObject) {
  return Boolean(object.deduplicatedCropUrl || object.cropUrl || object.deduplicatedObjectId)
}

function layoutFeedTags(objects: DetectedObject[], sourceSize: Size, containerSize: Size): FeedTagLayout[] {
  const placed: FeedTagLayout[] = []
  const safeEdge = 14
  for (const object of objects) {
    const nameWidth = [...object.name].reduce((width, character) => width + (character.charCodeAt(0) > 255 ? 12 : 7), 0)
    const tagExtent = Math.min(211, nameWidth + 99)
    const point = containTagPosition(object.tagPosition, sourceSize, containerSize)
    let left = Math.min(Math.max(point.x, safeEdge), Math.max(safeEdge, containerSize.width - safeEdge))
    let top = Math.min(Math.max(point.y, 82), Math.max(82, containerSize.height - 142))
    const nearby = placed.filter((item) => Math.abs(item.left - left) < 210 && Math.abs(item.top - top) < 54)
    let direction: FeedTagLayout['direction'] = left > containerSize.width * .58 ? 'left' : 'right'
    if (nearby.length) direction = nearby[nearby.length - 1].direction === 'left' ? 'right' : 'left'
    const roomOnLeft = left - safeEdge
    const roomOnRight = containerSize.width - safeEdge - left
    if (direction === 'left' && roomOnLeft < tagExtent && roomOnRight > roomOnLeft) direction = 'right'
    if (direction === 'right' && roomOnRight < tagExtent && roomOnLeft > roomOnRight) direction = 'left'
    const crowdedAnchors = placed.filter((item) => Math.abs(item.left - left) < 80 && Math.abs(item.top - top) < 28)
    if (crowdedAnchors.length) {
      const anchorOffset = 14 + Math.min(crowdedAnchors.length, 3) * 7
      left = Math.min(Math.max(left + (direction === 'left' ? -anchorOffset : anchorOffset), safeEdge), Math.max(safeEdge, containerSize.width - safeEdge))
      top = Math.min(Math.max(top + (crowdedAnchors.length % 2 ? -20 : 20), 82), Math.max(82, containerSize.height - 142))
    }
    left = direction === 'left'
      ? Math.min(Math.max(left, safeEdge + tagExtent), containerSize.width - safeEdge)
      : Math.max(Math.min(left, containerSize.width - safeEdge - tagExtent), safeEdge)
    const horizontalRange = (tagLeft: number, tagDirection: FeedTagLayout['direction'], extent: number) => tagDirection === 'left'
      ? [tagLeft - extent, tagLeft]
      : [tagLeft, tagLeft + extent]
    const [rangeStart, rangeEnd] = horizontalRange(left, direction, tagExtent)
    const minTop = 82; const maxTop = Math.max(minTop, containerSize.height - 142)
    const overlapsAt = (candidateTop: number) => placed.some((item) => {
      const [itemStart, itemEnd] = horizontalRange(item.left, item.direction, item.extent)
      const overlapsHorizontally = rangeStart < itemEnd + 10 && rangeEnd > itemStart - 10
      return overlapsHorizontally && Math.abs(item.top - candidateTop) < 48
    })
    const baseTop = top
    const candidates = [0, 54, -54, 108, -108, 162, -162]
      .map((offset) => Math.min(Math.max(baseTop + offset, minTop), maxTop))
      .filter((candidate, index, values) => values.indexOf(candidate) === index)
    top = candidates.find((candidate) => !overlapsAt(candidate)) ?? candidates[candidates.length - 1] ?? top
    placed.push({ object, left, top, direction, extent: tagExtent })
  }
  return placed
}

function FeedCard({ video, active, index }: { video: FeedVideo; active: boolean; index: number }) {
  const navigate = useNavigate(); const toast = useToast(); const setFurnitureLibraryPreview = useSceneStore((s) => s.setFurnitureLibraryPreview)
  const rootRef = useRef<HTMLElement>(null); const videoRef = useRef<HTMLVideoElement>(null); const abortRef = useRef<AbortController | null>(null); const searchAbortRef = useRef<AbortController | null>(null); const serialRef = useRef(0)
  const [paused, setPaused] = useState(true); const [muted, setMuted] = useState(true); const [liked, setLiked] = useState(false); const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'empty' | 'error'>('idle'); const [message, setMessage] = useState(''); const [detection, setDetection] = useState<DetectResponse | null>(null); const [containerSize, setContainerSize] = useState<Size>({ width: 0, height: 0 }); const [sourceSize, setSourceSize] = useState<Size>({ width: 0, height: 0 })
  const [sheetOpen, setSheetOpen] = useState(false); const [sheetLoading, setSheetLoading] = useState(false); const [sheetError, setSheetError] = useState(''); const [sheetProducts, setSheetProducts] = useState<ShopProduct[]>([]); const [selectedObject, setSelectedObject] = useState<DetectedObject | null>(null)
  const cancelRecognition = useCallback(() => {
    serialRef.current += 1
    abortRef.current?.abort()
    abortRef.current = null
    searchAbortRef.current?.abort()
    searchAbortRef.current = null
    setDetection(null)
    setStatus('idle')
    setSheetOpen(false)
    setSheetLoading(false)
    setSheetError('')
    setSheetProducts([])
    setSelectedObject(null)
  }, [])
  useEffect(() => { const root = rootRef.current; if (!root) return; const resize = () => setContainerSize({ width: root.clientWidth, height: root.clientHeight }); resize(); const observer = new ResizeObserver(resize); observer.observe(root); return () => observer.disconnect() }, [])
  useEffect(() => { const element = videoRef.current; if (!element) return; if (active) void element.play().catch(() => setPaused(true)); else { element.pause(); cancelRecognition() } }, [active, cancelRecognition])
  useEffect(() => () => { abortRef.current?.abort(); searchAbortRef.current?.abort() }, [])
  const recognize = useCallback(async () => {
    const element = videoRef.current; if (!element || !active || element.readyState < 2) return
    const time = element.currentTime; const serial = ++serialRef.current; abortRef.current?.abort(); const controller = new AbortController(); abortRef.current = controller
    setDetection(null); setStatus('loading'); setMessage('')
    let hash: string | undefined; try { hash = computeVideoDHash(element) } catch { hash = undefined }
    try { const result = await detectPausedFrame(video.id, time, hash, controller.signal); if (serial !== serialRef.current || !element.paused) return; setDetection(result); setStatus(result.objects.length ? 'success' : 'empty') }
    catch (reason) { if (controller.signal.aborted || serial !== serialRef.current) return; setMessage(reason instanceof Error ? reason.message : '识别暂时不可用'); setStatus('error') }
  }, [active, video.id])
  const closeSheet = useCallback(() => {
    searchAbortRef.current?.abort()
    searchAbortRef.current = null
    setSheetOpen(false)
    setSheetLoading(false)
    setSheetError('')
    setSelectedObject(null)
  }, [])
  const chooseObject = async (object: DetectedObject) => {
    if (!canSearchProducts(object)) {
      toast.show('当前标签暂无可用商品图')
      return
    }
    setSelectedObject(object)
    setSheetOpen(true)
    setSheetLoading(true)
    setSheetError('')
    setSheetProducts([])
    searchAbortRef.current?.abort()
    const controller = new AbortController()
    searchAbortRef.current = controller
    try {
      const products = await searchFeedProducts({
        videoId: video.id,
        deduplicatedObjectId: object.deduplicatedObjectId,
        cropUrl: object.deduplicatedCropUrl || object.cropUrl,
        objectId: object.id,
        label: object.label,
        hint: object.name || object.label,
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      setSheetProducts(products)
      if (!products.length) setSheetError('未找到相似商品')
    } catch (reason) {
      if (controller.signal.aborted) return
      setSheetError(reason instanceof Error ? reason.message : '搜图识商品失败')
    } finally {
      if (!controller.signal.aborted) setSheetLoading(false)
    }
  }
  const previewSelected = (product?: ShopProduct) => {
    if (!selectedObject || !detection || !selectedObject.prebuiltGlbUrl) {
      toast.show('家具模型暂时不可用')
      return
    }
    const candidateId = selectedObject.deduplicatedObjectId || selectedObject.id
    setFurnitureLibraryPreview({
      item: {
        id: `video-${video.id}-${candidateId}`,
        videoId: video.id,
        candidateId,
        representativeFrameId: detection.frameId,
        representativeObjectId: selectedObject.id,
        label: selectedObject.label,
        category: selectedObject.label,
        name: selectedObject.name,
        previewUrl: `/outputs/videos/${video.id}/generated/${candidateId}/reference_oblique_3quarter.png`,
        glbUrl: selectedObject.prebuiltGlbUrl,
        sizeBytes: 0,
        estimatedDimensions: selectedObject.estimatedDimensions,
      },
      product: product ?? sheetProducts[0] ?? null,
    })
    navigate('/home')
  }
  const tagLayouts = paused && detection ? layoutFeedTags(detection.objects, sourceSize, containerSize) : []
  return <article ref={rootRef} className='feed-card' data-feed-index={index}>
    <video ref={videoRef} className='feed-card__video' src={video.videoUrl} poster={video.coverUrl} muted={muted} playsInline loop preload={active ? 'auto' : 'metadata'} onLoadedMetadata={(event) => setSourceSize({ width: event.currentTarget.videoWidth, height: event.currentTarget.videoHeight })} onCanPlay={(event) => { if (active && event.currentTarget.paused) void event.currentTarget.play().catch(() => undefined) }} onPause={() => { setPaused(true); if (active) void recognize() }} onPlay={() => { setPaused(false); cancelRecognition() }} onSeeking={cancelRecognition} />
    <button className='feed-card__tap' type='button' aria-label={paused ? '继续播放' : '暂停识别'} onClick={() => { const element = videoRef.current; if (!element) return; if (element.paused) void element.play(); else element.pause() }} />
    <div className='feed-card__shade' />
    <header className='feed-card__header'><strong>QQ HOUSE</strong><div><span>关注</span><b>推荐</b></div></header>
    {paused && status === 'idle' && <div className='feed-card__pause'><Pause /></div>}
    {status === 'loading' && <div className='feed-status'><LoaderCircle className='spin' />正在匹配家具</div>}
    {(status === 'empty' || status === 'error') && <button className='feed-status is-action' type='button' onClick={() => void recognize()}>{status === 'error' && <AlertCircle />}{message || '当前画面没有可用家具'} · 重试</button>}
    {tagLayouts.map(({ object, left, top, direction }) => {
      const searchable = canSearchProducts(object)
      return <button key={object.id} className={`feed-tag is-${direction} ${searchable ? '' : 'is-disabled'}`} type='button' disabled={!searchable} style={{ left, top }} onClick={() => void chooseObject(object)}><span className='feed-tag__dot' /><span className='feed-tag__line' /><span className='feed-tag__bar'><strong>{object.name}</strong><small>{searchable ? '搜同款' : '暂无商品图'}</small></span></button>
    })}
    <aside className='feed-social' aria-label='视频操作'>
      <button type='button' className='feed-avatar' aria-label={`查看 ${video.author} 的主页`}><span>{video.author.slice(0, 1)}</span><Plus /></button>
      <button type='button' className={liked ? 'is-liked' : ''} aria-label='点赞' onClick={() => setLiked((value) => !value)}><Heart fill={liked ? 'currentColor' : 'none'} /><small>{liked ? '12.9w' : '12.8w'}</small></button>
      <button type='button' aria-label='评论'><MessageCircle /><small>238</small></button>
      <button type='button' aria-label='收藏'><Bookmark /><small>4.2w</small></button>
      <button type='button' aria-label='分享'><Share2 /><small>分享</small></button>
      <button type='button' className='feed-record' aria-label={muted ? '打开声音' : '静音'} onClick={() => setMuted((value) => !value)}>{muted ? <VolumeX /> : <Volume2 />}<Music2 /></button>
    </aside>
    <footer className='feed-card__copy'><strong>@{video.author}</strong><h1>{video.title}</h1><p>暂停视频，点击家具 Tag 搜同款商品</p><div>{video.furnitureHints.map((hint) => <span key={hint}>#{hint}</span>)}</div></footer>
    <ProductRecognizeSheet
      open={sheetOpen}
      loading={sheetLoading}
      error={sheetError}
      objectName={selectedObject?.name}
      products={sheetProducts}
      canPlace={Boolean(selectedObject?.prebuiltGlbUrl)}
      onClose={closeSheet}
      onPlace={previewSelected}
    />
  </article>
}

function FeedDock() {
  return <nav className='feed-dock' aria-label='Feed 底栏'>
    <button type='button' className='is-active' aria-label='首页'><Home /><span>首页</span></button>
    <button type='button' aria-label='朋友'><UsersRound /><span>朋友</span></button>
    <button type='button' className='feed-dock__create' aria-label='发布'><Plus /></button>
    <button type='button' aria-label='消息'><Inbox /><span>消息</span></button>
    <button type='button' aria-label='我'><UserRound /><span>我</span></button>
  </nav>
}

export function FeedPage() {
  const rootRef = useRef<HTMLDivElement>(null); const cycleSize = feedVideos.length; const middleCycle = 2; const [activeIndex, setActiveIndex] = useState(cycleSize * middleCycle)
  const loopVideos = Array.from({ length: 5 }, (_, cycle) => feedVideos.map((video) => ({ video, cycle }))).flat()
  useEffect(() => {
    const root = rootRef.current; if (!root || !cycleSize) return
    let frame = requestAnimationFrame(() => { root.scrollTop = root.clientHeight * cycleSize * middleCycle })
    const recenter = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const pageHeight = root.clientHeight; if (!pageHeight) return
        const index = Math.round(root.scrollTop / pageHeight)
        const shift = pageHeight * cycleSize * 2
        if (index < cycleSize) root.scrollTop += shift
        else if (index >= cycleSize * 4) root.scrollTop -= shift
      })
    }
    root.addEventListener('scroll', recenter, { passive: true })
    return () => { cancelAnimationFrame(frame); root.removeEventListener('scroll', recenter) }
  }, [cycleSize])
  useEffect(() => { const root = rootRef.current; if (!root) return; const observer = new IntersectionObserver((entries) => { const current = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; const index = Number((current?.target as HTMLElement | undefined)?.dataset.feedIndex); if (current?.intersectionRatio && current.intersectionRatio > .62 && Number.isInteger(index)) setActiveIndex(index) }, { root, threshold: [.62, .82] }); root.querySelectorAll('.feed-card').forEach((item) => observer.observe(item)); return () => observer.disconnect() }, [])
  return <div className='feed-experience'><div ref={rootRef} className='feed-page'>{loopVideos.map(({ video, cycle }, index) => <FeedCard key={`${cycle}-${video.id}`} video={video} active={index === activeIndex} index={index} />)}</div><FeedDock /></div>
}
