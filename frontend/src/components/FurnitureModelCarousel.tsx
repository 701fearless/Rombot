import { Move3D } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { GeneratedFurniture } from '@/types/scene'
import { ModelPreview3D } from './ModelPreview3D'

export function FurnitureModelCarousel({
  item,
  productName,
}: {
  item: GeneratedFurniture
  productName?: string
}) {
  const railRef = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState(0)
  const dimensions = item.estimatedDimensions

  useEffect(() => {
    setPage(0)
    railRef.current?.scrollTo({ left: 0 })
  }, [item.id])

  const goToPage = (index: number) => {
    const rail = railRef.current
    if (!rail) return
    rail.scrollTo({ left: rail.clientWidth * index, behavior: 'smooth' })
  }

  return <section className='furniture-model-carousel' aria-label={`${item.name} 模型预览与信息`}>
    <div
      className='furniture-model-carousel__rail'
      ref={railRef}
      onScroll={(event) => {
        const target = event.currentTarget
        setPage(Math.round(target.scrollLeft / Math.max(target.clientWidth, 1)))
      }}
    >
      <article className='furniture-model-carousel__slide is-model'>
        <ModelPreview3D glbUrl={item.glbUrl} name={item.name} />
        <p><Move3D />拖动旋转 · 双指或滚轮缩放</p>
      </article>
      <article className='furniture-model-carousel__slide is-info'>
        <div className='furniture-model-carousel__info'>
          <span>MODEL INFORMATION</span>
          <h2>模型信息</h2>
          <dl>
            <div><dt>模型名称</dt><dd>{item.name}</dd></div>
            <div><dt>对应商品</dt><dd>{productName || item.name}</dd></div>
            <div><dt>模型类别</dt><dd>{item.category}</dd></div>
            <div><dt>来源</dt><dd>视频 {item.videoId}</dd></div>
            <div><dt>文件</dt><dd>{item.sizeBytes ? `${(item.sizeBytes / 1024 / 1024).toFixed(1)} MB` : 'GLB 已生成'}</dd></div>
            {dimensions && <div><dt>尺寸</dt><dd>{dimensions.widthM.toFixed(2)} × {dimensions.depthM.toFixed(2)} × {dimensions.heightM.toFixed(2)}m</dd></div>}
          </dl>
        </div>
      </article>
    </div>
    <div className='furniture-model-carousel__pager' aria-label='模型展示页'>
      <button className={page === 0 ? 'is-active' : ''} type='button' aria-label='查看 3D 模型' onClick={() => goToPage(0)} />
      <button className={page === 1 ? 'is-active' : ''} type='button' aria-label='查看模型信息' onClick={() => goToPage(1)} />
    </div>
    <span className='furniture-model-carousel__hint'>{page === 0 ? '左滑查看模型信息' : '右滑返回 3D 模型'}</span>
  </section>
}
