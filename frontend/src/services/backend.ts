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
export function resetSceneSnapshot(sceneId: string) { return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(sceneId)}/reset`, { method: 'POST' }) }
export function listUploadedFurniture() { return json<UploadedFurniture[]>('/api/furniture/list') }
export function uploadFurniture(file: File) { const body = new FormData(); body.append('file', file); return json<UploadedFurniture & { message: string }>('/api/furniture/upload', { method: 'POST', body }) }
export async function deleteUploadedFurniture(id: string) { const response = await fetch(`/api/furniture/${encodeURIComponent(id)}`, { method: 'DELETE' }); if (!response.ok) throw await errorOf(response, '删除家具失败') }
export function requestRoomLayout(scene: Record<string, unknown>) { return json<RoomLayoutAdvice>('/api/room/room-layout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scene, enableAgents: false }) }) }
export function saveRuntimeWhitebox(snapshot: SceneSnapshot, file: Blob) { const body = new FormData(); body.append('file', file, 'edited.glb'); body.append('snapshot', JSON.stringify(snapshot)); return json<SceneSnapshot>(`/api/room/snapshots/${encodeURIComponent(snapshot.sceneId)}/whitebox`, { method: 'PUT', body }) }
