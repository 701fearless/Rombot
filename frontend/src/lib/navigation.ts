import type { FeedVideo, SpaceEntryParams } from "../types"

interface SpaceUrlInput {
  video: FeedVideo
  sceneId?: string
  time: number
  frameId: string
  objectId: string
  objectLabel: string
}

export function buildSpaceEntryParams({
  video,
  sceneId,
  time,
  frameId,
  objectId,
  objectLabel,
}: SpaceUrlInput): SpaceEntryParams {
  return {
    ...(sceneId ? { sceneId } : {}),
    videoId: video.id,
    time: time.toFixed(2),
    sceneType: video.sceneType,
    frameId,
    objectId,
    objectLabel,
  }
}

export function buildSpaceUrl(input: SpaceUrlInput): string {
  return `/space?${new URLSearchParams(
    Object.entries(buildSpaceEntryParams(input)),
  ).toString()}`
}
