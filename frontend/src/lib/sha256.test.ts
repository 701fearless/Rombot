import { describe, expect, it } from "vitest"

import { sha256Bytes } from "./sha256"

describe("sha256Bytes", () => {
  it("returns a lowercase 64-character browser SHA-256", async () => {
    const bytes = new TextEncoder().encode("room1").buffer
    await expect(sha256Bytes(bytes)).resolves.toBe(
      "b5edc2f9b9fb4418bd7bdf0a9f583ef216aeefc013f22d18347d542ced22f679",
    )
  })
})
