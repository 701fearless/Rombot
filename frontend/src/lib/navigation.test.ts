import { describe, expect, it } from "vitest"

import type { FeedVideo } from "../types"
import { buildSpaceUrl } from "./navigation"

const video: FeedVideo = {
  id: "2",
  title: "客厅",
  author: "测试",
  videoUrl: "/2.mp4",
  coverUrl: "/2.webp",
  sceneType: "living_room",
  furnitureHints: ["sofa"],
}

describe("buildSpaceUrl", () => {
  it("includes the complete handoff contract", () => {
    const url = buildSpaceUrl({
      video,
      sceneId: "room1",
      time: 12.4,
      frameId: "2_000003",
      objectId: "obj_sofa_001",
      objectLabel: "sofa",
    })
    const parsed = new URL(url, "https://example.test")
    expect(parsed.pathname).toBe("/space")
    expect(Object.fromEntries(parsed.searchParams)).toEqual({
      sceneId: "room1",
      videoId: "2",
      time: "12.40",
      sceneType: "living_room",
      frameId: "2_000003",
      objectId: "obj_sofa_001",
      objectLabel: "sofa",
    })
  })

  it("keeps legacy links usable when a room has not been chosen yet", () => {
    const url = buildSpaceUrl({
      video,
      time: 1,
      frameId: "2_000002",
      objectId: "obj_sofa_001",
      objectLabel: "sofa",
    })
    expect(new URL(url, "https://example.test").searchParams.has("sceneId")).toBe(false)
  })
})
