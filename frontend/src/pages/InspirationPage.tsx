import { Box, Check, ChevronRight, Move3D, Play, Sparkles, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import spaceImage from '@/assets/reference/space-3d-living.png'
import { ModelPreview3D } from '@/components/ModelPreview3D'
import { useToast } from '@/components/ToastProvider'
import { listGeneratedFurniture } from '@/services/backend'
import { useSceneStore } from '@/store'
import type { GeneratedFurniture } from '@/types/scene'

const categoryOrder = ['全部', '沙发', '床', '桌', '椅', '柜', '灯', '地毯', '软装', '装饰', '其他']

function shuffledCatalog(items: GeneratedFurniture[]) {
  const shuffled = [...items]
  let seed = 0x16f00d

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    seed = (seed * 1664525 + 1013904223) >>> 0
    const target = seed % (index + 1)
    ;[shuffled[index], shuffled[target]] = [shuffled[target], shuffled[index]]
  }

  return shuffled
}

function LibraryPreviewModal() {
  const toast = useToast()
  const preview = useSceneStore((state) => state.furnitureLibraryPreview)
  const setPreview = useSceneStore((state) => state.setFurnitureLibraryPreview)
  const library = useSceneStore((state) => state.furnitureLibrary)
  const addFurniture = useSceneStore((state) => state.addFurnitureToLibrary)
  const railRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(0)

  useEffect(() => {
    if (!preview) return
    setPage(0)
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setPreview(null)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [preview, setPreview])

  if (!preview) return null
  const { item, product } = preview
  const dimensions = item.estimatedDimensions
  const saved = library.some((candidate) => candidate.id === item.id)
  const goToPage = (index: number) => {
    const rail = railRef.current
    if (!rail) return
    rail.scrollTo({ left: rail.clientWidth * index, behavior: 'smooth' })
  }
  const saveToLibrary = () => {
    addFurniture(item)
    setPreview(null)
    toast.show(saved ? '家具已在家具库中' : `${item.name} 已加入家具库`)
  }

  return <div className='library-preview-modal' role='dialog' aria-modal='true' aria-labelledby='library-preview-title'>
    <button className='library-preview-modal__backdrop' type='button' aria-label='关闭家具预览' onClick={() => setPreview(null)} />
    <section className='library-preview-modal__card'>
      <header>
        <div><span className='eyebrow'>FURNITURE PREVIEW</span><h2 id='library-preview-title'>{item.name}</h2></div>
        <button type='button' aria-label='关闭' onClick={() => setPreview(null)}><X /></button>
      </header>
      <div
        ref={railRef}
        className='library-preview-modal__rail'
        onScroll={(event) => {
          const target = event.currentTarget
          setPage(Math.round(target.scrollLeft / Math.max(target.clientWidth, 1)))
        }}
      >
        <article className='library-preview-modal__slide is-model'>
          <ModelPreview3D glbUrl={item.glbUrl} name={item.name} />
          <p><Move3D />拖动旋转 · 双指或滚轮缩放</p>
        </article>
        <article className='library-preview-modal__slide is-info'>
          <div className='library-preview-modal__info'>
            <span>MODEL INFORMATION</span>
            <strong>模型信息</strong>
            <dl>
              <div><dt>模型名称</dt><dd>{item.name}</dd></div>
              <div><dt>对应商品</dt><dd>{product?.title || product?.productName || item.name}</dd></div>
              <div><dt>模型类别</dt><dd>{item.category}</dd></div>
              <div><dt>来源</dt><dd>视频 {item.videoId}</dd></div>
              <div><dt>模型</dt><dd>GLB 已生成</dd></div>
              {dimensions && <div><dt>尺寸</dt><dd>{dimensions.widthM.toFixed(2)} × {dimensions.depthM.toFixed(2)} × {dimensions.heightM.toFixed(2)}m</dd></div>}
            </dl>
          </div>
        </article>
      </div>
      <div className='library-preview-modal__pager' aria-label='预览页'>
        <button className={page === 0 ? 'is-active' : ''} type='button' aria-label='查看 3D 模型' onClick={() => goToPage(0)} />
        <button className={page === 1 ? 'is-active' : ''} type='button' aria-label='查看模型信息' onClick={() => goToPage(1)} />
      </div>
      <footer>
        <span>{page === 0 ? '左滑查看模型信息' : '右滑返回 3D 模型'}</span>
        <button className='primary-button' type='button' onClick={saveToLibrary}>{saved ? <Check /> : <Sparkles />}{saved ? '已在家具库' : '加入家具库'}</button>
      </footer>
    </section>
  </div>
}

export function InspirationPage() {
  const library = useSceneStore((state) => state.furnitureLibrary)
  const activeSceneId = useSceneStore((state) => state.activeSceneId)
  const [items, setItems] = useState<GeneratedFurniture[]>([])
  const [activeCategory, setActiveCategory] = useState('全部')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let live = true
    listGeneratedFurniture()
      .then((catalog) => {
        if (!live) return
        setItems(catalog)
        setError('')
      })
      .catch((reason) => {
        if (!live) return
        setError(reason instanceof Error ? reason.message : '模型目录暂时不可用')
      })
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [])

  const availableItems = useMemo(() =>
    items.filter((item) => !library.some((saved) => saved.id === item.id)),
  [items, library])
  const categories = useMemo(() => categoryOrder.filter((category) =>
    category === '全部' || availableItems.some((item) => item.category === category),
  ), [availableItems])
  useEffect(() => {
    if (!categories.includes(activeCategory)) setActiveCategory('全部')
  }, [activeCategory, categories])
  const mixedItems = useMemo(() => shuffledCatalog(availableItems), [availableItems])
  const visibleItems = useMemo(() =>
    activeCategory === '全部' ? mixedItems : availableItems.filter((item) => item.category === activeCategory),
  [activeCategory, availableItems, mixedItems])

  return <div className='surface-page inspiration-page'>
    <LibraryPreviewModal />
    <section className='page-intro inspiration-intro'>
      <div><span className='eyebrow'>INSPIRATION LIBRARY</span><h1>灵感</h1><p>真实生成的家具模型，喜欢就放进你的家。</p></div>
      <Link className='inspiration-intro__feed' to='/feed'><Play /><span>视频 Feed</span></Link>
    </section>

    <section className='inspiration-memory'>
      <img src={spaceImage} alt={`${activeSceneId} 客厅空间预览`} />
      <div className='inspiration-memory__veil' />
      <div className='inspiration-memory__copy'>
        <span>房屋记忆</span>
        <h2>法式复古之家 · 客厅</h2>
        <p>{activeSceneId} · 真实比例 · 随时继续</p>
      </div>
      <Link to={`/space?sceneId=${activeSceneId}`}>继续布置 <ChevronRight /></Link>
    </section>

    <section className='inspiration-catalog'>
      <div className='section-heading'>
        <div><h2>家具灵感</h2></div>
      </div>
      <div className='inspiration-filters' role='toolbar' aria-label='家具分类'>
        {categories.map((category) => <button
          type='button'
          key={category}
          className={activeCategory === category ? 'is-active' : ''}
          aria-pressed={activeCategory === category}
          onClick={() => setActiveCategory(category)}
        >{category}</button>)}
      </div>

      {loading && <div className='inspiration-grid' aria-label='正在加载模型目录'>
        {Array.from({ length: 6 }).map((_, index) => <div className='inspiration-skeleton' key={index}><span /><i /></div>)}
      </div>}
      {!loading && error && <div className='catalog-empty'><Box /><strong>模型目录加载失败</strong><p>{error}</p></div>}
      {!loading && !error && !visibleItems.length && <div className='catalog-empty'><Sparkles /><strong>这个分类还没有模型</strong><p>先看看其他家具灵感。</p></div>}
      {!loading && !error && !!visibleItems.length && <div className='inspiration-grid'>
        {visibleItems.map((item) => <Link className='generated-card' to={`/product/${encodeURIComponent(item.id)}`} key={item.id}>
          <div className='generated-card__media'>
            <img src={item.previewUrl} alt={`${item.name} 生成参考图`} loading='lazy' />
            <span><Move3D />3D</span>
          </div>
          <div className='generated-card__body'>
            <small>{item.category} · 视频 {item.videoId}</small>
            <strong>{item.name}</strong>
            <span>旋转查看模型 <ChevronRight /></span>
          </div>
        </Link>)}
      </div>}
    </section>
  </div>
}
