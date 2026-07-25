import { expect, test } from '@playwright/test'

test('Feed starts with videos 1-6 and can pause for detection', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('.feed-card')).toHaveCount(6)
  await expect(page.locator('.feed-card').first()).toContainText('自然材质')
  await expect(page.locator('.app-nav')).toHaveCount(0)
  await expect(page.getByRole('complementary', { name: '视频操作' }).first()).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Feed 底栏' })).toBeVisible()
  await expect(page.getByRole('button', { name: '评论' }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '发布' })).toBeVisible()
  await page.locator('.feed-card__video').first().evaluate(async (video) => { await (video as HTMLVideoElement).play() })
  await page.locator('.feed-card__tap').first().click()
  await expect(page.locator('.feed-status, .feed-tag').first()).toBeVisible({ timeout: 10_000 })
  await expect(page.locator('.feed-card').first().locator('.feed-tag')).toHaveCount(4)
})

test('legacy feed route redirects to root', async ({ page }) => {
  await page.goto('/feed')
  await expect(page).toHaveURL(/\/$/)
})

test('desktop demo flows from a cached Feed tag into room6 advice', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop-chrome', 'Primary interaction acceptance is desktop H5')
  await page.goto('/')
  const video = page.locator('.feed-card__video').first()
  await video.evaluate(async (node) => {
    const element = node as HTMLVideoElement
    element.currentTime = 1
    await element.play()
    element.pause()
  })
  const tag = page.locator('.feed-tag:not(.is-disabled)').first()
  await expect(tag).toBeVisible({ timeout: 10_000 })
  await tag.click()
  await expect(page).toHaveURL(/\/space\?sceneId=room6/)
  await expect(page.getByText('room6 空间编辑器')).toBeVisible()
  await expect(page.getByText('当前场景家具')).toBeVisible()
  await expect(page.getByText('无需手动上传 GLB')).toBeVisible()
  await page.getByRole('button', { name: '保存方案' }).click()
  await page.getByRole('button', { name: /完成摆放并查看建议/ }).click()
  await expect(page.getByText('布局建议')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByText('空间接口')).toBeVisible()
})
