import type { DetectResponse } from "../types"

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
