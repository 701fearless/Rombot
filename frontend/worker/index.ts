import analysis2 from "../../backend/outputs/videos/2/analysis.json"
import analysis3 from "../../backend/outputs/videos/3/analysis.json"
import analysis4 from "../../backend/outputs/videos/4/analysis.json"
import analysis6 from "../../backend/outputs/videos/6/analysis.json"
import analysis7 from "../../backend/outputs/videos/7/analysis.json"

interface Env {
  ASSETS: {
    fetch(request: Request): Promise<Response>
  }
}

interface AnalysisFrame {
  frameId: string
  time: number
  frameImageUrl?: string | null
  perceptualHash?: string | null
  objects: unknown[]
}

interface VideoAnalysis {
  videoId: string
  frames: AnalysisFrame[]
}

const analyses: Record<string, VideoAnalysis> = {
  "2": analysis2 as VideoAnalysis,
  "3": analysis3 as VideoAnalysis,
  "4": analysis4 as VideoAnalysis,
  "6": analysis6 as VideoAnalysis,
  "7": analysis7 as VideoAnalysis,
}

function json(payload: unknown, status = 200): Response {
  return Response.json(payload, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  })
}

function hashDistance(left: string, right: string): number {
  let value = BigInt(`0x${left}`) ^ BigInt(`0x${right}`)
  let distance = 0
  while (value) {
    distance += Number(value & 1n)
    value >>= 1n
  }
  return distance
}

function nearestFrame(analysis: VideoAnalysis, time: number, frameHash?: string): AnalysisFrame {
  const frames = [...analysis.frames].sort((left, right) => left.time - right.time)
  const exact = frames.find((frame) => Math.abs(frame.time - time) <= 1e-6)
  if (exact) return exact

  const previous = [...frames].reverse().find((frame) => frame.time < time)
  const following = frames.find((frame) => frame.time > time)
  const candidates = [previous, following].filter((frame): frame is AnalysisFrame => Boolean(frame))
  if (!candidates.length) throw new Error("Video analysis contains no frames")
  if (candidates.length === 1) return candidates[0]

  if (frameHash && /^[0-9a-f]{16}$/i.test(frameHash)) {
    const scored = candidates
      .filter((frame) => frame.perceptualHash && /^[0-9a-f]{16}$/i.test(frame.perceptualHash))
      .map((frame) => ({
        frame,
        distance: hashDistance(frameHash.toLowerCase(), frame.perceptualHash!.toLowerCase()),
        timeDistance: Math.abs(frame.time - time),
        followsPause: frame.time > time,
      }))
      .sort(
        (left, right) =>
          left.distance - right.distance ||
          left.timeDistance - right.timeDistance ||
          Number(left.followsPause) - Number(right.followsPause),
      )
    if (scored.length) return scored[0].frame
  }

  return candidates.sort(
    (left, right) =>
      Math.abs(left.time - time) - Math.abs(right.time - time) ||
      Number(left.time > time) - Number(right.time > time),
  )[0]
}

async function detect(request: Request): Promise<Response> {
  let input: { videoId?: string; time?: number; frameHash?: string }
  try {
    input = (await request.json()) as typeof input
  } catch {
    return json({ detail: "Request body must be JSON" }, 400)
  }

  if (!input.videoId || typeof input.time !== "number" || input.time < 0) {
    return json({ detail: "videoId and a non-negative time are required" }, 422)
  }
  if (input.frameHash && !/^[0-9a-f]{16}$/i.test(input.frameHash)) {
    return json({ detail: "frameHash must be a 16-character hexadecimal dHash" }, 422)
  }

  const analysis = analyses[input.videoId]
  if (!analysis) return json({ detail: "Video analysis not found" }, 404)
  const frame = nearestFrame(analysis, input.time, input.frameHash)
  return json({
    frameId: frame.frameId,
    frameImageUrl: null,
    objects: frame.objects,
  })
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url)

    if (url.pathname === "/health") {
      return json({ status: "ok", service: "rombot-feed" })
    }
    if (url.pathname === "/api/feed/detect" && request.method === "POST") {
      return detect(request)
    }
    if (url.pathname.startsWith("/api/")) {
      return json({ detail: "Not found" }, 404)
    }

    const assetResponse = await env.ASSETS.fetch(request)
    if (assetResponse.status !== 404) return assetResponse

    if (request.method === "GET" && request.headers.get("Accept")?.includes("text/html")) {
      return env.ASSETS.fetch(new Request(new URL("/index.html", request.url), request))
    }
    return assetResponse
  },
}
