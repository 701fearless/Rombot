import { lookupFeedProducts } from '@/data/feedProductMatches'
import type { ClipSearchResponse, ResolveReferenceResponse, ShopProduct } from '@/types/shop'
import type { DetectResponse, PrebuiltAsset, RoomLayoutAdvice, SceneSnapshot, UploadedFurniture } from '@/types/scene'

async function errorOf(response: Response, fallback: string) {
  try { const body = await response.json() as { detail?: string }; return new Error(body.detail || fallback) } catch { return new Error(fallback) }
}
async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) throw await errorOf(response, `${init?.method ?? 'GET'} ${url} 请求失败 (${response.status})`)
  return response.json() as Promise<T>
}
export async function detectPausedFrame(videoId: string, time: number, frameHash?: string, signal?: AbortSignal) {
  const controller = new AbortController(); const timer = window.setTimeout(() => controller.abort(), 8000)
  const abort = () => controller.abort(); signal?.addEventListener('abort', abort, { once: true })
  try { return await json<DetectResponse>('/api/feed/detect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ videoId, time, ...(frameHash ? { frameHash } : {}) }), signal: controller.signal }) }
  catch (error) { if (controller.signal.aborted && !signal?.aborted) throw new Error('识别请求超时，请重试'); throw error }
  finally { window.clearTimeout(timer); signal?.removeEventListener('abort', abort) }
}
export function getPrebuiltAsset(frameId: string, objectId: string) { return json<PrebuiltAsset>(`/api/feed/prebuilt-asset?${new URLSearchParams({ frameId, objectId })}`) }
export function getSceneSnapshot(sceneId: string) { return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(sceneId)}`) }
export function putSceneSnapshot(snapshot: SceneSnapshot) { return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(snapshot.sceneId)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(snapshot) }) }
export function resetSceneSnapshot(sceneId: string) { return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(snapshot.sceneId)}/reset`, { method: 'POST' }) }
export function listUploadedFurniture() { return json<UploadedFurniture[]>('/api/furniture/list') }
export function uploadFurniture(file: File) { const body = new FormData(); body.append('file', file); return json<UploadedFurniture & { message: string }>('/api/furniture/upload', { method: 'POST', body }) }
export async function deleteUploadedFurniture(id: string) { const response = await fetch(`/api/furniture/${encodeURIComponent(id)}`, { method: 'DELETE' }); if (!response.ok) throw await errorOf(response, '删除家具失败') }
export function requestRoomLayout(scene: Record<string, unknown>) { return json<RoomLayoutAdvice>('/api/room/room-layout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scene, enableAgents: false }) }) }
export function saveRuntimeWhitebox(snapshot: SceneSnapshot, file: Blob) { const body = new FormData(); body.append('file', file, 'edited.glb'); body.append('snapshot', JSON.stringify(snapshot)); return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(snapshot.sceneId)}/whitebox`, { method: 'PUT', body }) }

const feedSearchMemory = new Map<string, ShopProduct[]>()
const feedSearchInflight = new Map<string, Promise<ShopProduct[]>>()

function feedSearchKey(videoId: string, candidateId: string) {
  return `${videoId}::${candidateId}`
}

function cropFileName(cropUrl?: string | null) {
  if (!cropUrl) return ''
  try {
    return decodeURIComponent(cropUrl.split('?')[0]?.split('/').pop() || '')
  } catch {
    return cropUrl.split('/').pop() || ''
  }
}

export async function resolveShopReference(input: {
  videoId: string
  imageName: string
  signal?: AbortSignal
}): Promise<ResolveReferenceResponse | null> {
  const response = await fetch('/api/shop/resolve-reference', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ parentFolder: input.videoId, imageName: input.imageName }),
    signal: input.signal,
  })
  if (response.status === 404 || response.status === 400) return null
  if (!response.ok) throw await errorOf(response, '匹配 reference 失败')
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) return null
  return response.json() as Promise<ResolveReferenceResponse>
}

export async function getFeedClipCache(videoId: string, candidateId: string, signal?: AbortSignal): Promise<ShopProduct[] | null> {
  const params = new URLSearchParams({ videoId, candidateId })
  try {
    const response = await fetch(`/api/shop/feed-clip-cache?${params}`, { signal })
    if (response.status === 404) return null
    if (!response.ok) return null
    const contentType = response.headers.get('content-type') || ''
    if (!contentType.includes('application/json')) return null
    const payload = await response.json() as { results?: ShopProduct[] }
    const results = (payload.results ?? []).slice(0, 4)
    return results.length ? results : null
  } catch {
    return null
  }
}

export function clipSearchProducts(input: {
  cropUrl: string
  topK?: number
  textWeight?: number
  imageName?: string
  label?: string | null
  persist?: boolean
}, signal?: AbortSignal) {
  const label = input.label?.trim()
  return json<ClipSearchResponse>('/api/video/clip-search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      cropUrl: input.cropUrl,
      topK: input.topK ?? 4,
      textOnly: false,
      // Prefer reference image; light label weight keeps category on track (rug≠sofa).
      textWeight: input.textWeight ?? (label ? 0.35 : 0),
      persist: input.persist ?? true,
      ...(input.imageName ? { imageName: input.imageName } : {}),
      ...(label ? { hint: { label } } : {}),
    }),
    signal,
  })
}

/**
 * 1) 读本地 feed_clip_cache（含商品图快照，无需完整 product_index）
 * 2) 未命中：resolve reference → CLIP 搜同款，并落盘
 * 3) 失败才回退写死 demo
 */
export async function searchFeedProducts(input: {
  videoId: string
  deduplicatedObjectId?: string | null
  cropUrl?: string | null
  objectId?: string | null
  label?: string | null
  hint?: string
  signal?: AbortSignal
}): Promise<ShopProduct[]> {
  const candidateId = input.deduplicatedObjectId?.trim() || ''
  const cropName = cropFileName(input.cropUrl)
  const cacheId = candidateId || cropName || input.objectId?.trim() || input.label?.trim() || 'unknown'
  const key = feedSearchKey(input.videoId, cacheId)

  const memorized = feedSearchMemory.get(key)
  if (memorized?.length) return memorized

  const inflight = feedSearchInflight.get(key)
  if (inflight) return inflight

  const task = (async () => {
    // Disk cache first — works without CLIP / full IKEA index.
    for (const id of [candidateId, cacheId].filter(Boolean)) {
      const disk = await getFeedClipCache(input.videoId, id, input.signal)
      if (disk?.length) {
        feedSearchMemory.set(key, disk)
        return disk
      }
    }

    try {
      const resolveNames = [
        candidateId,
        cropName,
        candidateId && input.videoId ? `${input.videoId}_${candidateId}_crop.jpg` : '',
        input.objectId?.trim() || '',
      ].filter(Boolean)

      let referenceUrl = ''
      let imageName = candidateId || cropName || cacheId
      for (const name of resolveNames) {
        const resolved = await resolveShopReference({
          videoId: input.videoId,
          imageName: name,
          signal: input.signal,
        })
        if (resolved?.referenceUrl) {
          referenceUrl = resolved.referenceUrl
          imageName = resolved.matchedFolder || name
          break
        }
      }

      const queryUrl = referenceUrl || input.cropUrl?.trim() || ''
      if (!queryUrl) throw new Error('未找到 reference / crop')

      const live = await clipSearchProducts({
        cropUrl: queryUrl,
        topK: 4,
        imageName,
        label: input.label || undefined,
        persist: true,
      }, input.signal)

      const results = (live.results ?? []).slice(0, 4)
      if (results.length) {
        feedSearchMemory.set(key, results)
        return results
      }
      throw new Error('CLIP 未返回商品')
    } catch {
      const fallback = lookupFeedProducts({
        videoId: input.videoId,
        deduplicatedObjectId: input.deduplicatedObjectId,
        objectId: input.objectId,
        label: input.label,
        hint: input.hint,
      })
      if (fallback.length) feedSearchMemory.set(key, fallback)
      return fallback
    }
  })()

  feedSearchInflight.set(key, task)
  try {
    return await task
  } finally {
    feedSearchInflight.delete(key)
  }
}
