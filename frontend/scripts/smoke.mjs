/**
 * 前端冒烟测试（Playwright + Firefox）：
 * 验证主页一屏布局、解析/下载流程、介绍页与 VIP 页、移动端适配，并输出截图。
 * 用法：node scripts/smoke.mjs [--screenshots-dir <dir>]
 */
import { firefox, devices } from 'playwright'

const BASE = 'http://127.0.0.1:8000'
const SHOTS = process.argv.includes('--screenshots-dir')
  ? process.argv[process.argv.indexOf('--screenshots-dir') + 1]
  : 'smoke-screenshots'

const results = []
function check(name, ok, extra = '') {
  results.push({ name, ok, extra })
  console.log(`${ok ? 'PASS' : 'FAIL'} | ${name}${extra ? ' | ' + extra : ''}`)
}

async function waitForText(page, text, timeoutMs) {
  try {
    await page.waitForFunction(
      (t) => document.body.innerText.includes(t),
      text,
      { timeout: timeoutMs },
    )
    return true
  } catch {
    return false
  }
}

async function main() {
  const browser = await firefox.launch({ headless: true })
  const consoleErrors = []
  const pageErrors = []

  // ---------- 桌面端主页 ----------
  // reducedMotion 让入场动画瞬时完成，截图与断言结果稳定可复现
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  page.on('console', (m) => m.type() === 'error' && consoleErrors.push(m.text()))
  page.on('pageerror', (e) => pageErrors.push(String(e)))

  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  check('页面标题包含 SnapDown', (await page.title()).includes('SnapDown'))
  check(
    'Hero 标题为「万能视频即刻下载」',
    await page.evaluate(() => document.querySelector('h1')?.textContent?.replace(/\s/g, '').includes('万能视频即刻下载')),
  )
  check('输入框存在', !!(await page.$('input#video-url')))

  const buttons = await page.evaluate(() =>
    [...document.querySelectorAll('button')].map((b) => b.textContent.trim()).join('|'),
  )
  check('主按钮文案为「开始解析」', buttons.includes('开始解析'))
  check('不存在「开始下载」按钮', !buttons.includes('开始下载'))
  check('导航包含「为什么选 SnapDown」', (await page.evaluate(() => document.body.innerText)).includes('为什么选 SnapDown'))
  check('导航包含「开通VIP」', buttons.includes('开通VIP'))
  check('平台标签渲染', (await page.evaluate(() => document.body.innerText)).includes('#B站'))
  check(
    '主页无「为什么选瞬下」旧文案',
    !(await page.evaluate(() => document.body.innerText)).includes('为什么选瞬下'),
  )
  check(
    '页脚不出现 yt-dlp / 技术栈',
    await page.evaluate(() => {
      const t = document.querySelector('footer')?.innerText || ''
      return !/yt-dlp|FastAPI|Vue 3/i.test(t) && t.includes('Payson')
    }),
  )

  const bodyBg = await page.evaluate(() => getComputedStyle(document.body).backgroundImage)
  check('主页背景为渐变白（非纯白）', /gradient/.test(bodyBg), bodyBg.slice(0, 70))

  const homeScroll = await page.evaluate(() => ({
    scrollHeight: document.documentElement.scrollHeight,
    inner: window.innerHeight,
  }))
  check(
    '主页 900px 视口内不滚动（一屏可见）',
    homeScroll.scrollHeight <= homeScroll.inner + 2,
    `${homeScroll.scrollHeight}px / ${homeScroll.inner}px`,
  )
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${SHOTS}/01-home-desktop.png` })

  // ---------- 下载记录抽屉 ----------
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('下载记录'))
    btn?.click()
  })
  check('下载记录抽屉可打开', await waitForText(page, '重启后自动清空', 5000))
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${SHOTS}/05-history-drawer.png` })
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)
  check(
    'ESC 可关闭抽屉',
    await page.evaluate(() => !document.body.innerText.includes('重启后自动清空')),
  )

  // ---------- 为什么选 SnapDown ----------
  await page.goto(`${BASE}/#/why`, { waitUntil: 'networkidle', timeout: 30000 })
  check('介绍页渲染愿景区块', await waitForText(page, '我们的愿景', 8000))
  check('介绍页渲染核心能力', await waitForText(page, '核心能力', 3000))
  check('介绍页渲染 Pro 会员区块', await waitForText(page, 'SnapDown Pro', 3000))
  check('介绍页渲染 FAQ', await waitForText(page, '常见问题', 3000))
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${SHOTS}/06-why-desktop.png` })
  await page.screenshot({ path: `${SHOTS}/06b-why-full.png`, fullPage: true })

  // ---------- VIP 订阅页 ----------
  await page.goto(`${BASE}/#/vip`, { waitUntil: 'networkidle', timeout: 30000 })
  check('VIP 页渲染权益区块', await waitForText(page, '会员能拿到什么', 8000))
  check('VIP 页渲染套餐', await waitForText(page, '年度会员', 3000))
  check('VIP 页渲染对比表', await waitForText(page, '免费版 vs Pro 会员', 3000))
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${SHOTS}/07-vip-desktop.png` })
  await page.screenshot({ path: `${SHOTS}/07b-vip-full.png`, fullPage: true })

  // 「立即开通 VIP」必须滚动到本页套餐区（曾经因 href="#plans" 被误当成路由而跳回主页）
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(200)
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.trim() === '立即开通 VIP')
    btn?.click()
  })
  await page.waitForTimeout(1200)
  const jump = await page.evaluate(() => {
    const heading = [...document.querySelectorAll('h2')].find((h) => h.textContent.includes('选择适合你的方案'))
    const rect = heading?.getBoundingClientRect()
    return {
      hash: location.hash,
      scrollY: Math.round(window.scrollY),
      headingInView: !!rect && rect.top >= 0 && rect.top < window.innerHeight,
      onVipPage: !!document.querySelector('#plans'),
    }
  })
  check(
    'VIP 页「立即开通 VIP」滚动到本页套餐区（不跳主页）',
    jump.hash === '#/vip' && jump.scrollY > 0 && jump.headingInView && jump.onVipPage,
    JSON.stringify(jump),
  )
  await page.screenshot({ path: `${SHOTS}/07c-vip-plans-anchor.png` })

  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('立即开通 年度会员'))
    btn?.click()
  })
  check('点击开通弹出内测提示', await waitForText(page, '内测中', 5000))
  await page.waitForTimeout(600)
  await page.screenshot({ path: `${SHOTS}/08-vip-dialog.png` })
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)

  // ---------- 主页解析 / 下载流程 ----------
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  const url = 'https://www.bilibili.com/video/BV1GJ411x7h7'
  await page.fill('input#video-url', url)
  await page.click('button[type="submit"]')
  const parsed = await waitForText(page, '选择清晰度', 30000)
  check('解析出结果卡片', parsed)
  if (parsed) {
    const chips = await page.evaluate(() => document.querySelectorAll('[role="radiogroup"] button').length)
    check('清晰度选项 ≥ 2 个', chips >= 2, `${chips} 个`)
    const title = await page.evaluate(() => document.querySelector('h2')?.textContent || '')
    check('视频标题显示', title.length > 0, title.slice(0, 30))
    await page.waitForTimeout(600)
    await page.screenshot({ path: `${SHOTS}/02-result-desktop.png` })

    await page.evaluate(() => {
      const btns = [...document.querySelectorAll('button')]
      btns.find((b) => b.textContent.includes('下载 最佳画质'))?.click()
    })
    const done = await waitForText(page, '保存到本地', 180000)
    check('下载完成态出现', done)
    if (done) {
      await page.waitForTimeout(600)

      // 下载完成后应收起清晰度选择（避免"选了也没用"的死控件），改为清爽成功卡片
      const doneState = await page.evaluate(() => {
        const card = document.querySelector('.card')
        const text = card?.innerText || ''
        return {
          hasRadiogroup: !!document.querySelector('[role="radiogroup"]'),
          hasDoneTitle: text.includes('下载完成'),
          hasHeightTag: /\b1080P\b/.test(text),
          hasSizeTag: /(KB|MB|GB)/.test(text),
          hasSave: text.includes('保存到本地'),
          hasReset: [...document.querySelectorAll('button')].some((b) => b.textContent.includes('再来一个')),
        }
      })
      check('下载完成后收起清晰度选择（不再有死控件）', !doneState.hasRadiogroup)
      check(
        '下载完成卡片含标题与分辨率/体积标签、保存与再来一个',
        doneState.hasDoneTitle &&
          doneState.hasHeightTag &&
          doneState.hasSizeTag &&
          doneState.hasSave &&
          doneState.hasReset,
        JSON.stringify(doneState),
      )

      await page.screenshot({ path: `${SHOTS}/03-done-desktop.png` })
    }

    // ---------- 下载记录：封面 + 标题 ----------
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('下载记录'))
      btn?.click()
    })
    await page.waitForTimeout(900)
    try {
      await page.waitForFunction(
        () => {
          const img = document.querySelector('[role="dialog"] img')
          return !!img && img.naturalWidth > 0
        },
        undefined,
        { timeout: 10000 },
      )
    } catch {
      /* 超时后仍继续断言，由断言给出失败详情 */
    }
    const thumb = await page.evaluate(() => {
      const img = document.querySelector('[role="dialog"] img')
      return img
        ? { src: img.getAttribute('src'), loaded: img.naturalWidth, complete: img.complete }
        : null
    })
    check('下载记录显示视频封面（图片真实加载）', !!thumb && thumb.loaded > 0, JSON.stringify(thumb))
    check(
      '下载记录显示视频标题而非裸链接',
      await page.evaluate(() =>
        (document.querySelector('[role="dialog"]')?.innerText || '').includes('Never Gonna Give You Up'),
      ),
    )

    // ---------- 下载记录：分辨率 / 体量 / 下载时间 标签 ----------
    const tagText = await page.evaluate(() => {
      // 取最新一条（第一张卡片）的标签区，避免旧记录干扰
      const card = document.querySelector('[role="dialog"] .card')
      return card?.innerText || ''
    })
    check('下载记录显示分辨率标签', /\b1080P\b/.test(tagText), tagText.replace(/\n/g, ' ').slice(0, 80))
    check('下载记录显示视频体量标签', /(KB|MB|GB)/.test(tagText), tagText.replace(/\n/g, ' ').slice(0, 80))
    check(
      '下载记录显示下载时间（精确到分钟）',
      /\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(tagText),
      tagText.replace(/\n/g, ' ').slice(0, 80),
    )
    await page.screenshot({ path: `${SHOTS}/05b-history-thumb.png` })
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)

    // ---------- 「再来一个」回到刚进主页时的初始状态 ----------
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
    await page.waitForTimeout(400)
    const beforeReset = await page.evaluate(() => Math.round(window.scrollY))
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('再来一个'))
      btn?.click()
    })
    await page.waitForTimeout(1000)
    const afterReset = await page.evaluate(() => ({
      inputValue: document.querySelector('input#video-url')?.value ?? null,
      hasResultCard: !!document.querySelector('[role="radiogroup"]'),
      chipsVisible: document.body.innerText.includes('支持平台：'),
      scrollY: Math.round(window.scrollY),
      oneScreen: document.documentElement.scrollHeight <= window.innerHeight + 2,
    }))
    check(
      '「再来一个」回到初始主页（清空链接 + 无结果卡片 + 回到顶部 + 恢复一屏）',
      afterReset.inputValue === '' &&
        !afterReset.hasResultCard &&
        afterReset.chipsVisible &&
        afterReset.scrollY === 0 &&
        afterReset.oneScreen,
      `点击前 scrollY=${beforeReset} → ${JSON.stringify(afterReset)}`,
    )
    await page.screenshot({ path: `${SHOTS}/05c-after-reset.png` })
  }

  // ---------- 页脚年份动态化（伪造系统时间为 2027） ----------
  const clockPage = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  await clockPage.addInitScript(() => {
    const RealDate = Date
    const fixed = new RealDate('2027-05-20T10:00:00+08:00').getTime()
    class MockDate extends RealDate {
      constructor(...args) {
        if (args.length) super(...args)
        else super(fixed)
      }
      static now() {
        return fixed
      }
    }
    window.Date = MockDate
  })
  await clockPage.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  const footerText = await clockPage.evaluate(() => document.querySelector('footer')?.innerText || '')
  check(
    '页脚版权年份随系统时间动态变化（伪 2027 年）',
    footerText.includes('© 2027 SnapDown'),
    footerText.match(/©\s*\d{4}/)?.[0] || '未找到年份',
  )
  await clockPage.close()

  // ---------- 「粘贴」直接写入剪贴板内容（不弹二次操作） ----------
  const pastePage = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  await pastePage.addInitScript(() => {
    // 模拟 navigator.clipboard.readText()：直接返回一条已复制的链接。
    // 用 stub 锁住"点击粘贴 → 直接填入输入框"这条链路（真实剪贴板在无头 Firefox 不可用）。
    Object.defineProperty(navigator, 'clipboard', {
      value: { readText: () => Promise.resolve('https://www.bilibili.com/video/BV1GJ411x7h7') },
      configurable: true,
    })
  })
  await pastePage.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  await pastePage.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.trim() === '粘贴')
    btn?.click()
  })
  await pastePage.waitForTimeout(300)
  const pastedValue = await pastePage.evaluate(() => document.querySelector('input#video-url')?.value || '')
  check(
    '「粘贴」点击后直接填入剪贴板内容（无需二次操作）',
    pastedValue === 'https://www.bilibili.com/video/BV1GJ411x7h7',
    pastedValue,
  )

  // 失败路径：浏览器拒绝读剪贴板时，应聚焦输入框并提示手动粘贴
  await pastePage.evaluate(() => {
    const clearBtn = [...document.querySelectorAll('button')].find(
      (b) => b.getAttribute('aria-label') === '清空输入',
    )
    clearBtn?.click()
    Object.defineProperty(navigator, 'clipboard', {
      value: { readText: () => Promise.reject(new Error('denied')) },
      configurable: true,
    })
  })
  await pastePage.waitForTimeout(200)
  await pastePage.evaluate(() => {
    // 按钮文案会在"粘贴/已粘贴"之间切换，用 includes 匹配更稳
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('粘贴'))
    btn?.click()
  })
  await pastePage.waitForTimeout(400)
  const failState = await pastePage.evaluate(() => ({
    hint: document.body.innerText.includes('Ctrl+V'),
    focused: document.activeElement?.id === 'video-url',
  }))
  check('剪贴板被拒时提示手动粘贴并聚焦输入框', failState.hint && failState.focused, JSON.stringify(failState))
  await pastePage.close()

  // ---------- 静态资源缓存策略（避免浏览器停留在旧构建） ----------
  const indexResp = await fetch(BASE)
  const indexHtml = await indexResp.text()
  const bundlePath = indexHtml.match(/\/assets\/index-[\w-]+\.js/)?.[0]
  const bundleResp = await fetch(`${BASE}${bundlePath}`)
  const bundleText = await bundleResp.text()
  check(
    '入口 HTML 禁用强缓存（避免跑旧构建）',
    /no-cache/.test(indexResp.headers.get('cache-control') || ''),
    indexResp.headers.get('cache-control') || '(无)',
  )
  check(
    'assets 指纹资源可长期强缓存',
    /immutable/.test(bundleResp.headers.get('cache-control') || ''),
    bundleResp.headers.get('cache-control') || '(无)',
  )
  check(
    '前端产物不含 execCommand("paste")（避免 Chromium「粘贴(P)」确认气泡）',
    !bundleText.includes('execCommand'),
  )

  // ---------- 未知 hash 兜底：不应停在"路由落空"状态 ----------
  const strayPage = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  await strayPage.goto(`${BASE}/#features`, { waitUntil: 'networkidle', timeout: 30000 })
  await strayPage.waitForTimeout(600)
  const stray = await strayPage.evaluate(() => ({
    hash: location.hash,
    isHome: document.body.innerText.includes('万能视频') && !!document.querySelector('input#video-url'),
  }))
  check('未知 hash 自动回主页并清理地址栏', stray.hash === '#/' && stray.isHome, JSON.stringify(stray))
  await strayPage.close()

  // ---------- 移动端 ----------
  const mobileContext = await browser.newContext({ ...devices['iPhone 13'], reducedMotion: 'reduce' })
  const mobile = await mobileContext.newPage()
  mobile.on('pageerror', (e) => pageErrors.push('mobile: ' + String(e)))
  await mobile.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  const noHScroll = await mobile.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
  check('移动端无横向滚动', noHScroll)
  check(
    '移动端 Hero 渲染',
    await mobile.evaluate(() => document.querySelector('h1')?.textContent?.replace(/\s/g, '').includes('万能视频即刻下载')),
  )
  check('移动端可见开通VIP', await mobile.evaluate(() => document.body.innerText.includes('开通VIP')))
  await mobile.waitForTimeout(600)
  await mobile.screenshot({ path: `${SHOTS}/04-home-mobile.png` })
  await mobile.screenshot({ path: `${SHOTS}/04b-home-mobile-full.png`, fullPage: true })
  await mobile.goto(`${BASE}/#/vip`, { waitUntil: 'networkidle', timeout: 30000 })
  await mobile.screenshot({ path: `${SHOTS}/09-vip-mobile.png`, fullPage: true })
  await mobileContext.close()

  check('无页面 JS 错误', pageErrors.length === 0, pageErrors.slice(0, 3).join(' ; '))
  check('无控制台错误', consoleErrors.length === 0, consoleErrors.slice(0, 3).join(' ; '))

  const failed = results.filter((r) => !r.ok)
  console.log(`\n===== 冒烟测试: ${results.length - failed.length}/${results.length} 通过 =====`)
  await browser.close()
  process.exit(failed.length ? 1 : 0)
}

main().catch((e) => {
  console.error('SMOKE ERROR:', e.message)
  process.exit(2)
})
