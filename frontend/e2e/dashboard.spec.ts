import { expect, test } from '@playwright/test'
test('dashboard exposes the snapshot and layout contracts', async ({ page }) => { await page.goto('/dashboard'); await expect(page.getByText('PUT /api/room/snapshots/room6/whitebox')).toBeVisible(); await expect(page.getByText('POST /api/room/room-layout')).toBeVisible() })
