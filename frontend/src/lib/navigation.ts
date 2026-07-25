import type { FeedVideo, SpaceEntryParams } from "../types"

interface SpaceUrlInput {
  video: FeedVideo
  time: number
  frameId: string
  objectId: string
  objectLabel: string
}

export function buildSpaceEntryParams({
  video,
  time,
  frameId,
  objectId,
  objectLabel,
}: SpaceUrlInput): SpaceEntryParams {
  return {
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
