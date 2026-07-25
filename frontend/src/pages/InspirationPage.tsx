import { Box, ChevronRight, Move3D, Play, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import spaceImage from '@/assets/reference/space-3d-living.png'
import { listGeneratedFurniture } from '@/services/backend'
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

export function InspirationPage() {
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

  const categories = useMemo(() => categoryOrder.filter((category) =>
    category === '全部' || items.some((item) => item.category === category),
  ), [items])
  const mixedItems = useMemo(() => shuffledCatalog(items), [items])
  const visibleItems = useMemo(() =>
    activeCategory === '全部' ? mixedItems : items.filter((item) => item.category === activeCategory),
  [activeCategory, items, mixedItems])

  return <div className='surface-page inspiration-page'>
    <section className='page-intro inspiration-intro'>
      <div><span className='eyebrow'>INSPIRATION LIBRARY</span><h1>灵感</h1><p>真实生成的家具模型，喜欢就放进你的家。</p></div>
      <Link className='inspiration-intro__feed' to='/feed'><Play /><span>视频 Feed</span></Link>
    </section>

    <section className='inspiration-memory'>
      <img src={spaceImage} alt='room6 客厅空间预览' />
      <div className='inspiration-memory__veil' />
      <div className='inspiration-memory__copy'>
        <span>房屋记忆</span>
        <h2>法式复古之家 · 客厅</h2>
        <p>room6 · 真实比例 · 随时继续</p>
      </div>
      <Link to='/space?sceneId=room6'>继续布置 <ChevronRight /></Link>
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
