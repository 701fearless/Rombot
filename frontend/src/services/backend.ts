import type { DetectResponse, GeneratedFurniture, PrebuiltAsset, RoomLayoutAdvice, SceneSnapshot, SkillAdviceResponse, SkillAdviceScenario, UploadedFurniture } from '@/types/scene'
import type { ClipSearchResponse, ResolveReferenceResponse, ShopProduct } from '@/types/shop'

async function errorOf(response: Response, fallback: string) {
  try { const body = await response.json() as { detail?: string }; return new Error(body.detail || fallback) } catch { return new Error(fallback) }
}
async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) throw await errorOf(response, `${init?.method ?? 'GET'} ${url} 请求失败 (${response.status})`)
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.toLowerCase().includes('application/json')) throw new Error(`${url} 返回了非 JSON 内容，请检查本机后端接口路径`)
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
export function resetSceneSnapshot(sceneId: string) { return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(sceneId)}/reset`, { method: 'POST' }) }
export function listUploadedFurniture() { return json<UploadedFurniture[]>('/api/furniture/list') }
export function listGeneratedFurniture() { return json<GeneratedFurniture[]>('/api/furniture/generated') }
export function uploadFurniture(file: File) { const body = new FormData(); body.append('file', file); return json<UploadedFurniture & { message: string }>('/api/furniture/upload', { method: 'POST', body }) }
export async function deleteUploadedFurniture(id: string) { const response = await fetch(`/api/furniture/${encodeURIComponent(id)}`, { method: 'DELETE' }); if (!response.ok) throw await errorOf(response, '删除家具失败') }
export function requestRoomLayout(scene: Record<string, unknown>) { return json<RoomLayoutAdvice>('/api/room/room-layout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scene, enableAgents: false }) }) }
export function requestSkillAdvice(sceneId: string, scenarioId: SkillAdviceScenario, profile: Record<string, unknown>) {
  return json<SkillAdviceResponse>(`/api/room/snapshots/${encodeURIComponent(sceneId)}/skill-advice`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenarioId, profile }),
  })
}

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
      textWeight: input.textWeight ?? (label ? 0.35 : 0),
      persist: input.persist ?? true,
      ...(input.imageName ? { imageName: input.imageName } : {}),
      ...(label ? { hint: { label } } : {}),
    }),
    signal,
  })
}

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
    for (const id of [candidateId, cacheId].filter(Boolean)) {
      const cached = await getFeedClipCache(input.videoId, id, input.signal)
      if (cached?.length) {
        feedSearchMemory.set(key, cached)
        return cached
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
        const resolved = await resolveShopReference({ videoId: input.videoId, imageName: name, signal: input.signal })
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
      if (!results.length) throw new Error('CLIP 未返回商品')
      feedSearchMemory.set(key, results)
      return results
    } catch (error) {
      if (input.signal?.aborted) throw error
      throw error instanceof Error ? error : new Error('搜同款失败')
    }
  })()

  feedSearchInflight.set(key, task)
  try {
    return await task
  } finally {
    feedSearchInflight.delete(key)
  }
}
