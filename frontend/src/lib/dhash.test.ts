import { describe, expect, it } from "vitest"

import { differenceHashFromRgba } from "./dhash"

function makeGradient(descending: boolean): Uint8ClampedArray {
  const pixels = new Uint8ClampedArray(9 * 8 * 4)
  for (let row = 0; row < 8; row += 1) {
    for (let column = 0; column < 9; column += 1) {
      const value = descending ? 240 - column * 20 : 40 + column * 20
      const offset = (row * 9 + column) * 4
      pixels[offset] = value
      pixels[offset + 1] = value
      pixels[offset + 2] = value
      pixels[offset + 3] = 255
    }
  }
  return pixels
}

describe("differenceHashFromRgba", () => {
  it("returns a fixed 16-character hexadecimal hash", () => {
    expect(differenceHashFromRgba(makeGradient(true))).toBe("ffffffffffffffff")
    expect(differenceHashFromRgba(makeGradient(false))).toBe("0000000000000000")
  })

  it("rejects frames with the wrong dimensions", () => {
    expect(() => differenceHashFromRgba(new Uint8ClampedArray(4))).toThrow(
      "dHash expects a 9×8 RGBA frame",
    )
  })
})
