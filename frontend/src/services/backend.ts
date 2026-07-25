import type { DetectResponse, PrebuiltAsset, SceneSnapshot } from '@/types/scene'

async function readError(response: Response, fallback: string): Promise<Error> {
  try {
    const payload = (await response.json()) as { detail?: string }
    return new Error(payload.detail || fallback)
  } catch {
    return new Error(fallback)
  }
}

export async function detectPausedFrame(videoId: string, time: number, frameHash?: string, signal?: AbortSignal) {
  const timeoutController = new AbortController()
  const timeoutId = setTimeout(() => timeoutController.abort(), 8000)
  const abort = () => timeoutController.abort()
  signal?.addEventListener('abort', abort, { once: true })

  try {
    const response = await fetch('/api/feed/detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ videoId, time, ...(frameHash ? { frameHash } : {}) }),
      signal: timeoutController.signal,
    })
    if (!response.ok) throw await readError(response, `识别失败（${response.status}）`)
    return (await response.json()) as DetectResponse
  } catch (error) {
    if (timeoutController.signal.aborted && !signal?.aborted) {
      throw new Error('识别请求超时，请重试')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
    signal?.removeEventListener('abort', abort)
  }
}

export async function getPrebuiltAsset(frameId: string, objectId: string) {
  const query = new URLSearchParams({ frameId, objectId })
  const response = await fetch(`/api/feed/prebuilt-asset?${query.toString()}`)
  if (!response.ok) throw await readError(response, `家具模型未缓存（${response.status}）`)
  return (await response.json()) as PrebuiltAsset
}

export async function getSceneSnapshot(sceneId: string) {
  const response = await fetch(`/api/room/snapshots/${encodeURIComponent(sceneId)}`)
  if (!response.ok) throw await readError(response, `户型快照读取失败（${response.status}）`)
  return (await response.json()) as SceneSnapshot
}

export async function putSceneSnapshot(snapshot: SceneSnapshot) {
  const response = await fetch(`/api/room/snapshots/${encodeURIComponent(snapshot.sceneId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(snapshot),
  })
  if (!response.ok) throw await readError(response, `方案保存失败（${response.status}）`)
  return (await response.json()) as SceneSnapshot
}

export async function resetSceneSnapshot(sceneId: string) {
  const response = await fetch(`/api/room/snapshots/${encodeURIComponent(sceneId)}/reset`, {
    method: 'POST',
  })
  if (!response.ok) throw await readError(response, `方案重置失败（${response.status}）`)
  return (await response.json()) as SceneSnapshot
}
