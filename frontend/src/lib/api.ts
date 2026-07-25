import type {
  DetectResponse,
  FloorplanPreset,
  FloorplanReconstructResponse,
  PlacementCandidate,
  PlacementCheckResponse,
  PrebuiltAsset,
  SceneResponse,
} from "../types"

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? ""
const API_BASE_URL = configuredBaseUrl.replace(/\/$/, "")

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

interface DetectPausedFrameInput {
  videoId: string
  time: number
  frameHash: string
  signal?: AbortSignal
}

export async function detectPausedFrame({
  videoId,
  time,
  frameHash,
  signal,
}: DetectPausedFrameInput): Promise<DetectResponse> {
  const response = await fetch(apiUrl("/api/feed/detect"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ videoId, time, frameHash }),
    signal,
  })

  if (!response.ok) {
    let message = `识别请求失败（${response.status}）`
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) message = payload.detail
    } catch {
      // Keep the concise status message when the response is not JSON.
    }
    throw new Error(message)
  }

  return (await response.json()) as DetectResponse
}

interface ReconstructFloorplanInput {
  image: string
  signal?: AbortSignal
}

export async function reconstructFloorplan({
  image,
  signal,
}: ReconstructFloorplanInput): Promise<FloorplanReconstructResponse> {
  const response = await fetch(apiUrl("/api/floorplan/reconstruct"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image }),
    signal,
  })

  if (!response.ok) {
    let message = `户型识别失败（${response.status}）`
    try {
      const payload = (await response.json()) as { detail?: string | Array<{ msg?: string }> }
      if (typeof payload.detail === "string") message = payload.detail
      else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((item) => item.msg).filter(Boolean).join("；") || message
      }
    } catch {
      // Keep the status-based fallback for non-JSON errors.
    }
    throw new Error(message)
  }

  return (await response.json()) as FloorplanReconstructResponse
}

async function readApiError(response: Response, fallback: string): Promise<Error> {
  let message = fallback
  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload.detail) message = payload.detail
  } catch {
    // Keep the caller's fallback for non-JSON responses.
  }
  return new Error(message)
}

export async function listFloorplanPresets(
  signal?: AbortSignal,
): Promise<FloorplanPreset[]> {
  const response = await fetch(apiUrl("/api/floorplan/presets"), { signal })
  if (!response.ok) {
    throw await readApiError(response, `户型预设读取失败（${response.status}）`)
  }
  const payload = (await response.json()) as { presets: FloorplanPreset[] }
  return payload.presets
}

export async function getFloorplanPreset(
  sceneId: string,
  signal?: AbortSignal,
): Promise<FloorplanPreset> {
  const response = await fetch(
    apiUrl(`/api/floorplan/presets/${encodeURIComponent(sceneId)}`),
    { signal },
  )
  if (!response.ok) {
    throw await readApiError(response, `户型预设不存在（${response.status}）`)
  }
  return (await response.json()) as FloorplanPreset
}

export async function getPrebuiltAsset(
  frameId: string,
  objectId: string,
  signal?: AbortSignal,
): Promise<PrebuiltAsset> {
  const query = new URLSearchParams({ frameId, objectId })
  const response = await fetch(apiUrl(`/api/feed/prebuilt-asset?${query.toString()}`), {
    signal,
  })
  if (!response.ok) {
    throw await readApiError(response, `家具模型未预生成（${response.status}）`)
  }
  return (await response.json()) as PrebuiltAsset
}

export async function saveFloorplanWhitebox(
  sceneId: string,
  glb: ArrayBuffer,
  signal?: AbortSignal,
): Promise<{ sceneId: string; whiteboxGlbUrl: string; bytesWritten: number }> {
  const response = await fetch(
    apiUrl(`/api/floorplan/presets/${encodeURIComponent(sceneId)}/whitebox`),
    {
      method: "PUT",
      headers: { "Content-Type": "model/gltf-binary" },
      body: glb,
      signal,
    },
  )
  if (!response.ok) {
    throw await readApiError(response, `保存户型 GLB 失败（${response.status}）`)
  }
  return (await response.json()) as {
    sceneId: string
    whiteboxGlbUrl: string
    bytesWritten: number
  }
}

export async function placementCheck(input: {
  candidate: PlacementCandidate
  scene: SceneResponse
  sceneId?: string
  enableAgents?: boolean
  signal?: AbortSignal
}): Promise<PlacementCheckResponse> {
  const response = await fetch(apiUrl("/api/room/placement-check"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate: input.candidate,
      scene: input.scene,
      sceneId: input.sceneId ?? input.scene.sceneId,
      enableAgents: input.enableAgents ?? false,
    }),
    signal: input.signal,
  })
  if (!response.ok) {
    throw await readApiError(response, `摆放检测失败（${response.status}）`)
  }
  return (await response.json()) as PlacementCheckResponse
}
