import { expect, test } from "@playwright/test"
import path from "node:path"

const room1Image = path.resolve(
  process.cwd(),
  "../backend/sample_data/floorplans/room1.png",
)

test("preprocessed room and cached furniture load in one viewer", async ({ page }) => {
  const forbiddenRequests: string[] = []
  page.on("request", (request) => {
    if (
      request.url().includes("/api/floorplan/reconstruct") ||
      request.url().includes("/api/feed/select-object")
    ) {
      forbiddenRequests.push(request.url())
    }
  })

  await page.goto("/space")
  await page.locator('input[type="file"]').setInputFiles(room1Image)
  await page.getByRole("button", { name: "使用这个预处理户型" }).click()

  await expect(page).toHaveURL(/\/feed\?sceneId=room1$/)

  await page.route("**/api/feed/detect", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        frameId: "2_000002",
        frameImageUrl: "/outputs/videos/2/frames/2_000002.jpg",
        objects: [
          {
            id: "obj_sofa_001",
            label: "sofa",
            name: "沙发",
            confidence: 0.94,
            bbox: [100, 420, 840, 1500],
            tagPosition: [0.5, 0.58],
            deduplicatedObjectId: "candidate_sofa_001",
            estimatedDimensions: { widthM: 2.2, heightM: 0.85, depthM: 0.9 },
            prebuiltGlbUrl:
              "/outputs/videos/2/generated/candidate_sofa_001/generated_model.glb",
          },
        ],
      }),
    })
  })

  const firstVideo = page.locator("video").first()
  await expect
    .poll(() => firstVideo.evaluate((video: HTMLVideoElement) => video.readyState))
    .toBeGreaterThanOrEqual(2)
  await page.locator(".feed-item").first().click({ position: { x: 70, y: 280 } })
  await page.getByRole("button", { name: "选择沙发，放进我的户型" }).click()

  await expect(page).toHaveURL(/\/space\?sceneId=room1/)
  await expect(page.locator(".floorplan-viewer canvas")).toBeVisible()
  await expect(page.locator(".floorplan-viewer")).toHaveAttribute("data-status", "ready")
  await expect(page.getByText("沙发已放入户型")).toBeVisible()

  await page.getByRole("button", { name: "家具向右", exact: true }).click()
  await page.getByRole("button", { name: "家具向右旋转" }).click()
  await page.getByRole("button", { name: "放大家具" }).click()
  await expect(page.locator(".floorplan-viewer canvas")).toBeVisible()

  await page.reload()
  await expect(page.locator(".floorplan-viewer")).toHaveAttribute("data-status", "ready")
  expect(forbiddenRequests).toEqual([])
})

test("an unknown image stays on the preset selection step", async ({ page }) => {
  await page.goto("/space")
  await page.locator('input[type="file"]').setInputFiles({
    name: "unknown.png",
    mimeType: "image/png",
    buffer: Buffer.from("not-a-preset"),
  })
  await page.getByRole("button", { name: "使用这个预处理户型" }).click()
  await expect(page.getByText(/不在比赛预处理户型中/)).toBeVisible()
  await expect(page).toHaveURL(/\/space$/)
})
