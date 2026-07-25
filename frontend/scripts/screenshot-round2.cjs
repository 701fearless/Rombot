// 本轮改动验证截图：设计 Tab（三端口+资产架）/ 发现（纯 Feed）/ 摆放页（建议+方向入口）/ 生活场景页
const { chromium } = require('playwright')

const BASE = 'http://localhost:10086'
const shots = [
  { path: '/#/pages/remodel/index', name: 'design', fullPage: true, wait: 4600 },
  { path: '/#/pages/discover/index', name: 'discover', fullPage: true, wait: 2500 },
  { path: '/#/pages/flow/place/index?homeId=home_new&roomId=r_new_living', name: 'place', fullPage: true, wait: 3000 },
  { path: '/#/pages/direction/index?homeId=home_new&roomId=r_new_living', name: 'direction', fullPage: true, wait: 2500 },
]

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
  })
  page.on('console', (m) => {
    if (m.type() === 'error') console.log('[console.error]', m.text().slice(0, 200))
  })
  page.on('pageerror', (e) => console.log('[pageerror]', String(e).slice(0, 300)))

  for (const s of shots) {
    await page.goto(BASE + s.path, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
    await page.waitForTimeout(s.wait)
    await page.screenshot({ path: `shots/${s.name}.png`, fullPage: s.fullPage })
    console.log(`shot: shots/${s.name}.png`)
  }
  // 方向页交互：选「养宠」→ 三动作展开
  await page.goto(BASE + '/#/pages/direction/index?homeId=home_new&roomId=r_new_living', { waitUntil: 'networkidle' }).catch(() => {})
  await page.waitForTimeout(2000)
  await page.click('.direction-picker__pill:first-child')
  await page.waitForTimeout(600)
  await page.screenshot({ path: 'shots/direction-picked.png', fullPage: true })
  console.log('shot: shots/direction-picked.png')
  await browser.close()
})()
