import { expect, test } from "@playwright/test"

test("handoff dashboard exposes live data and the complete OpenAPI inventory", async ({ page }) => {
  await page.goto("/dashboard")

  await expect(page.getByRole("heading", { name: "家装视频 Feed 前端交接看板" })).toBeVisible()
  await expect(page.getByText("本地后端在线")).toBeVisible()
  await expect(page.locator(".video-status-card")).toHaveCount(5)
  await expect(page.locator(".video-ready.is-ready")).toHaveCount(5)
  await expect(page.locator(".endpoint-card")).toHaveCount(15)

  await page.getByPlaceholder("搜索路径、功能或分组").fill("/api/feed/detect")
  await expect(page.locator(".endpoint-card")).toHaveCount(1)
  await expect(page.locator(".endpoint-card code").first()).toHaveText("/api/feed/detect")
})

test("dashboard links to the working feed and API reference", async ({ page }) => {
  await page.goto("/dashboard")
  await expect(page.getByRole("link", { name: "打开可交互 Feed" })).toHaveAttribute("href", "/feed")
  await expect(page.getByRole("link", { name: /Swagger/ })).toHaveAttribute("href", "/docs")
})
