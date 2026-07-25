import { expect, test } from '@playwright/test'

test('room6 editor renders a nonblank canvas and editor controls', async ({ page }) => {
  await page.goto('/space?sceneId=room6')
  await expect(page.getByText('room6 空间编辑器')).toBeVisible()
  const canvas = page.locator('[data-testid="scene-canvas"] canvas')
  await expect(canvas).toBeVisible()
  await page.waitForTimeout(500)
  const pixels = await canvas.evaluate((node) => {
    const source = node as HTMLCanvasElement
    const probe = document.createElement('canvas'); probe.width = 8; probe.height = 8
    const context = probe.getContext('2d'); context?.drawImage(source, 0, 0, 8, 8)
    return [...(context?.getImageData(0, 0, 8, 8).data ?? [])].some((value, index) => index % 4 !== 3 && value > 8)
  })
  expect(pixels).toBe(true)
  await expect(page.getByRole('button', { name: /保存方案/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /完成摆放并查看建议/ })).toBeVisible()
})

test('all public routes support direct refresh', async ({ page }) => {
  for (const route of ['/home', '/discover', '/me', '/recognize', '/suggest', '/recommend', '/complete', '/dashboard']) {
    await page.goto(route)
    await page.reload()
    await expect(page.locator('#root')).not.toBeEmpty()
  }
})
