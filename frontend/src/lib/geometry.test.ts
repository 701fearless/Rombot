import { describe, expect, it } from "vitest"

import { coverTagPosition } from "./geometry"

describe("coverTagPosition", () => {
  it("keeps a centered tag centered after object-fit cover cropping", () => {
    const point = coverTagPosition(
      [0.5, 0.5],
      { width: 1080, height: 1920 },
      { width: 390, height: 844 },
    )
    expect(point.x).toBeCloseTo(195)
    expect(point.y).toBeCloseTo(422)
  })

  it("accounts for horizontally cropped video content", () => {
    const left = coverTagPosition(
      [0, 0.5],
      { width: 1080, height: 1920 },
      { width: 390, height: 844 },
    )
    expect(left.x).toBeLessThan(0)
  })
})
