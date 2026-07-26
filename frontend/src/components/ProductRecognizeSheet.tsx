import { ChevronLeft, LoaderCircle, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ShopProduct } from '@/types/shop'

function formatPrice(product: ShopProduct) {
  const value = Number(product.price)
  if (!Number.isFinite(value)) return '—'
  return `¥${value % 1 === 0 ? value.toFixed(0) : value.toFixed(2)}`
}

function matchHint(product: ShopProduct) {
  return product.category || product.subcategory || '本地商城'
}

async function fetchProductDetail(productId: string, signal?: AbortSignal): Promise<ShopProduct | null> {
  try {
    const response = await fetch(`/api/shop/products/${encodeURIComponent(productId)}`, { signal })
    if (!response.ok) return null
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) return null
    return await response.json() as ShopProduct
  } catch {
    return null
  }
}

export interface ProductRecognizeSheetProps {
  open: boolean
  loading: boolean
  error?: string
  objectName?: string
  products: ShopProduct[]
  canPlace?: boolean
  placing?: boolean
  onClose: () => void
  onPlace?: () => void
  onOpenProduct?: (product: ShopProduct) => void
}

export function ProductRecognizeSheet({
  open,
  loading,
  error,
  objectName,
  products,
  canPlace = true,
  placing = false,
  onClose,
  onPlace,
  onOpenProduct,
}: ProductRecognizeSheetProps) {
  const [detail, setDetail] = useState<ShopProduct | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    if (!open) {
      setDetail(null)
      setDetailLoading(false)
    }
  }, [open])

  if (!open) return null
  const top = products.slice(0, 4)

  const openDetail = async (product: ShopProduct) => {
    onOpenProduct?.(product)
    setDetail(product)
    setDetailLoading(true)
    const controller = new AbortController()
    const enriched = await fetchProductDetail(product.productId, controller.signal)
    setDetail(enriched ? { ...product, ...enriched } : product)
    setDetailLoading(false)
  }

  return (
    <div className='product-sheet' role='dialog' aria-modal='true' aria-label='搜图识商品'>
      <button className='product-sheet__backdrop' type='button' aria-label='关闭商品卡' onClick={onClose} />
      <section className='product-sheet__panel'>
        <header className='product-sheet__tabs'>
          {detail ? (
            <button type='button' className='product-sheet__back' onClick={() => setDetail(null)}>
              <ChevronLeft size={18} />返回同款
            </button>
          ) : (
            <div>
              <button type='button' className='is-active'>综合</button>
              <button type='button'>商品</button>
            </div>
          )}
          <button className='product-sheet__close' type='button' aria-label='关闭' onClick={onClose}><X size={18} /></button>
        </header>

        {!detail && (
          <>
            <div className='product-sheet__cta'>
              <p>这个家具看着不错，要不要放进家里试试效果？</p>
              <button
                type='button'
                className='product-sheet__room'
                disabled={!canPlace || !onPlace || placing}
                onClick={() => onPlace?.()}
              >
                {placing ? '进入空间…' : '一键室用'}
              </button>
            </div>
            {objectName ? <p className='product-sheet__caption'>识别到 · {objectName}</p> : null}
            {loading && (
              <div className='product-sheet__state'><LoaderCircle className='spin' />正在匹配 reference 并搜同款…</div>
            )}
            {!loading && error && <div className='product-sheet__state is-error'>{error}</div>}
            {!loading && !error && top.length === 0 && (
              <div className='product-sheet__state'>未找到相似商品</div>
            )}
            {!loading && !error && top.length > 0 && (
              <div className='product-sheet__grid'>
                {top.map((product) => (
                  <button
                    key={product.productId}
                    type='button'
                    className='product-sheet__card'
                    onClick={() => void openDetail(product)}
                  >
                    <span className='product-sheet__thumb'>
                      {product.imageUrl ? <img src={product.imageUrl} alt='' loading='lazy' /> : null}
                    </span>
                    <strong>{product.title || product.productName || product.productId}</strong>
                    <em>{formatPrice(product)}</em>
                    <small>{matchHint(product)}</small>
                  </button>
                ))}
              </div>
            )}
            <footer className='product-sheet__footer'>
              <button type='button' className='product-sheet__ask' disabled>
                <Search size={16} />接着问
              </button>
              <button type='button' className='product-sheet__more' onClick={onClose}>查看更多</button>
            </footer>
          </>
        )}

        {detail && (
          <div className='product-sheet__detail'>
            <div className='product-sheet__detail-media'>
              {detail.imageUrl ? <img src={detail.imageUrl} alt='' /> : <div className='product-sheet__detail-placeholder' />}
            </div>
            <div className='product-sheet__detail-body'>
              <strong>{detail.title || detail.productName || detail.productId}</strong>
              <em>{formatPrice(detail)}</em>
              <small>{matchHint(detail)}</small>
              {detailLoading && <p className='product-sheet__detail-meta'><LoaderCircle className='spin' size={14} /> 加载详情…</p>}
              <div className='product-sheet__detail-section'>
                <h4>品类</h4>
                <p>{detail.category || detail.subcategory || '—'}</p>
              </div>
              <div className='product-sheet__detail-section'>
                <h4>尺寸</h4>
                <p>{detail.sizeText || detail.measurementsText || '—'}</p>
              </div>
              <div className='product-sheet__detail-section'>
                <h4>描述</h4>
                <p>{detail.description || '暂无描述'}</p>
              </div>
              {detail.features?.length ? (
                <div className='product-sheet__detail-section'>
                  <h4>亮点</h4>
                  <ul>{detail.features.slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul>
                </div>
              ) : null}
            </div>
            <footer className='product-sheet__detail-actions'>
              <button type='button' className='product-sheet__room' disabled={!canPlace || !onPlace || placing} onClick={() => onPlace?.()}>
                {placing ? '进入空间…' : '一键室用'}
              </button>
              <button type='button' className='product-sheet__more' onClick={() => setDetail(null)}>返回列表</button>
            </footer>
          </div>
        )}
      </section>
    </div>
  )
}
