import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveShopReference } from './backend'

describe('resolveShopReference', () => {
  afterEach(() => vi.restoreAllMocks())

  it('treats a legacy backend 405 as an unavailable optional reference route', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Method Not Allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await expect(resolveShopReference({ videoId: '1', imageName: 'chair.jpg' })).resolves.toBeNull()
    expect(fetchMock).toHaveBeenCalledWith('/api/shop/resolve-reference', expect.objectContaining({ method: 'POST' }))
  })
})
