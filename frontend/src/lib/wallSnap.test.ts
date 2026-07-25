import { describe, expect, it } from "vitest"

import { inferWallLockAxis, snapWallPosition } from "./wallSnap"

describe("wallSnap", () => {
  it("locks axis-aligned walls to their long axis", () => {
    expect(inferWallLockAxis(4, 0.2)).toBe("x")
    expect(inferWallLockAxis(0.2, 3)).toBe("z")
    expect(inferWallLockAxis(1, 1)).toBeNull()
  })

  it("snaps free axis to nearby wall anchors and grid", () => {
    const snapped = snapWallPosition({
      x: 0.04,
      z: 1.03,
      lockAxis: "x",
      lockValue: -1.2,
      anchorsX: [0, 1.5],
      anchorsZ: [0, 1.0, 2.0],
      bounds: { x: 3, z: 2 },
      grid: 0.1,
      threshold: 0.12,
    })
    expect(snapped.x).toBeCloseTo(-1.2, 5)
    expect(snapped.z).toBeCloseTo(1.0, 5)
    expect(snapped.guideZ).toBeCloseTo(1.0, 5)
    expect(snapped.snapped).toBe(true)
  })

  it("clamps into room bounds", () => {
    const snapped = snapWallPosition({
      x: 9,
      z: -9,
      bounds: { x: 3, z: 2 },
      grid: 0.1,
      threshold: 0.05,
    })
    expect(snapped.x).toBeLessThanOrEqual(3)
    expect(snapped.z).toBeGreaterThanOrEqual(-2)
  })
})
