// H5 预览截图脚本：模拟 iPhone 视口截取各页面，供 UI 自查
// 用法：node scripts/screenshot.cjs（需先用 node scripts/preview-h5.cjs 10086 起本地服务）
const { chromium } = require('playwright')

const BASE = 'http://localhost:10086'
const shots = [
  // 设计（开屏只播一次：先访问设计页等播完，后续页面不再播）
  { path: '/#/pages/remodel/index', name: 'remodel', fullPage: true, wait: 5200 },
  { path: '/#/pages/myhome/index', name: 'myhome', fullPage: true, wait: 2500 },
  { path: '/#/pages/direction/index', name: 'direction', fullPage: true, wait: 2500 },
  {
    path: '/#/pages/direction/index',
    name: 'direction-selected',
    fullPage: true,
    wait: 800,
    clickText: '养宠',
  },
  { path: '/#/pages/discover/index', name: 'discover', fullPage: true, wait: 2500 },
  { path: '/#/pages/discover/scene/index?id=scene_pet', name: 'scene', fullPage: true, wait: 2500 },
  {
    path: '/#/pages/flow/place/index?homeId=home_tmpl&roomId=r_tmpl_living',
    name: 'place',
    fullPage: false,
    wait: 2500,
  },
]

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({
    viewport: { width: 440, height: 956 }, // iPhone 16 Pro Max 逻辑画布
    deviceScaleFactor: 1,
    isMobile: true,
    hasTouch: true,
  })
  page.on('console', (m) => {
    if (m.type() === 'error') console.log('[console.error]', m.text().slice(0, 200))
  })
  page.on('pageerror', (e) => console.log('[pageerror]', String(e).slice(0, 300)))

  for (const s of shots) {
    await page.goto(BASE + s.path, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
    await page.waitForTimeout(s.wait) // 等开屏/入场动画与 mock 延迟
    if (s.clickText) {
      await page.getByText(s.clickText, { exact: true }).first().click()
      await page.waitForTimeout(900)
    }
    await page.screenshot({ path: `shots/${s.name}.png`, fullPage: s.fullPage })
    console.log(`shot: shots/${s.name}.png`)
  }
  await browser.close()
})()
