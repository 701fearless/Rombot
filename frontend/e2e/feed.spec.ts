import { expect, test } from "@playwright/test"

test("mobile feed pauses, renders furniture tags, and hands off to space", async ({ page }) => {
  await page.route("**/api/feed/detect", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        frameId: "2_000003",
        frameImageUrl: "/outputs/videos/2/frames/example.jpg",
        objects: [
          {
            id: "obj_sofa_001",
            label: "sofa",
            name: "沙发",
            confidence: 0.94,
            bbox: [100, 420, 840, 1500],
            tagPosition: [0.5, 0.58],
          },
        ],
      }),
    })
  })

  await page.goto("/")
  await expect(page.locator(".feed-item")).toHaveCount(5)
  await expect(page.getByText("奶油色客厅，把松弛感装进日常")).toBeVisible()

  const firstVideo = page.locator("video").first()
  await expect(firstVideo).toHaveJSProperty("paused", false)
  await expect
    .poll(() => firstVideo.evaluate((element: HTMLVideoElement) => element.readyState))
    .toBeGreaterThanOrEqual(2)
  await page.locator(".feed-item").first().click({ position: { x: 80, y: 300 } })

  const tag = page.getByRole("button", { name: "选择沙发，进入我的小屋" })
  await expect(tag).toBeVisible()
  await tag.click()

  await expect(page).toHaveURL(/\/space\?/)
  await expect(page.getByText("沙发，已经送到小屋门口")).toBeVisible()
  const url = new URL(page.url())
  expect(url.searchParams.get("videoId")).toBe("2")
  expect(url.searchParams.get("frameId")).toBe("2_000003")
  expect(url.searchParams.get("objectId")).toBe("obj_sofa_001")
})

test("space route survives a direct page load", async ({ page }) => {
  await page.goto(
    "/space?videoId=4&time=8.20&sceneType=living_room&frameId=4_000002&objectId=obj_sofa_002&objectLabel=sofa",
  )
  await expect(page.getByText("沙发，已经送到小屋门口")).toBeVisible()
  await expect(page.getByText("#4")).toBeVisible()
})
