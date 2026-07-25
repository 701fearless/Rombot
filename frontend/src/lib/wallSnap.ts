/** Magnetic snap helpers for sandbox wall editing (viewer XZ, meters). */

export interface WallSnapBounds {
  x: number
  z: number
}

export interface WallSnapInput {
  x: number
  z: number
  /** Keep this axis fixed (axis-aligned walls). */
  lockAxis?: "x" | "z" | null
  lockValue?: number
  anchorsX?: number[]
  anchorsZ?: number[]
  bounds: WallSnapBounds
  /** Grid step in meters. */
  grid?: number
  /** Snap distance in meters. */
  threshold?: number
}

export interface WallSnapResult {
  x: number
  z: number
  snapped: boolean
  guideX: number | null
  guideZ: number | null
  label: string
}

function uniqueSorted(values: number[], epsilon = 1e-4): number[] {
  const sorted = [...values].sort((a, b) => a - b)
  const out: number[] = []
  for (const value of sorted) {
    if (!out.length || Math.abs(out[out.length - 1] - value) > epsilon) {
      out.push(value)
    }
  }
  return out
}

function nearestAnchor(
  value: number,
  anchors: number[],
  threshold: number,
): { value: number; distance: number } | null {
  let best: { value: number; distance: number } | null = null
  for (const anchor of anchors) {
    const distance = Math.abs(value - anchor)
    if (distance > threshold) continue
    if (!best || distance < best.distance) {
      best = { value: anchor, distance }
    }
  }
  return best
}

function snapToGrid(value: number, grid: number): number {
  if (grid <= 1e-9) return value
  return Math.round(value / grid) * grid
}

export function inferWallLockAxis(sizeX: number, sizeZ: number): "x" | "z" | null {
  if (sizeX > sizeZ * 1.35) return "x"
  if (sizeZ > sizeX * 1.35) return "z"
  return null
}

export function snapWallPosition(input: WallSnapInput): WallSnapResult {
  const grid = input.grid ?? 0.1
  const threshold = input.threshold ?? 0.12
  const anchorsX = uniqueSorted([0, ...(input.anchorsX ?? [])])
  const anchorsZ = uniqueSorted([0, ...(input.anchorsZ ?? [])])

  let x = input.x
  let z = input.z
  if (input.lockAxis === "x" && input.lockValue !== undefined) x = input.lockValue
  if (input.lockAxis === "z" && input.lockValue !== undefined) z = input.lockValue

  let guideX: number | null = null
  let guideZ: number | null = null
  const labels: string[] = []

  if (input.lockAxis !== "x") {
    const hit = nearestAnchor(x, anchorsX, threshold)
    if (hit) {
      x = hit.value
      guideX = hit.value
      labels.push(Math.abs(hit.value) < 1e-6 ? "对齐中线 X" : "对齐墙体 X")
    } else {
      const gridX = snapToGrid(x, grid)
      if (Math.abs(gridX - x) <= threshold) {
        x = gridX
        labels.push("网格")
      }
    }
  }

  if (input.lockAxis !== "z") {
    const hit = nearestAnchor(z, anchorsZ, threshold)
    if (hit) {
      z = hit.value
      guideZ = hit.value
      labels.push(Math.abs(hit.value) < 1e-6 ? "对齐中线 Z" : "对齐墙体 Z")
    } else {
      const gridZ = snapToGrid(z, grid)
      if (Math.abs(gridZ - z) <= threshold) {
        z = gridZ
        if (!labels.includes("网格")) labels.push("网格")
      }
    }
  }

  // Final hard grid for free axes when already close after anchor snap
  if (input.lockAxis !== "x") x = snapToGrid(x, grid)
  if (input.lockAxis !== "z") z = snapToGrid(z, grid)

  const limitX = Math.max(input.bounds.x, 0.5)
  const limitZ = Math.max(input.bounds.z, 0.5)
  x = Math.max(-limitX, Math.min(limitX, x))
  z = Math.max(-limitZ, Math.min(limitZ, z))

  return {
    x,
    z,
    snapped: labels.length > 0 || guideX !== null || guideZ !== null,
    guideX,
    guideZ,
    label: labels.join(" · "),
  }
}
