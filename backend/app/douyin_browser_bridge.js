/**
 * 抖音详情接口的「真实浏览器会话」桥。
 *
 * 为什么需要它：
 *   抖音 Web 端 `aweme/v1/web/aweme/detail/` 现在要求一整套签名参数
 *   （`a_bogus` + `msToken` + `verifyFp`/`fp` + secsdk 的
 *   `uifid` + `timestamp` + `x-secsdk-web-signature`）。其中 secsdk 三件套由页面里
 *   的 `secsdk`/`bdms` 运行时在真实浏览器环境中生成（依赖 ECDSA 会话密钥与服务器
 *   签发的 ticket），纯 Python 复现不现实。因此后端在直连 403 时改用本脚本：
 *   在 headless Firefox 里打开视频页，让页内运行时自己补全签名，再用页内 `fetch`
 *   取详情 JSON。
 *
 * 用法（由后端 `backend/app/douyin.py` 调用，不面向用户直接使用）：
 *   node douyin_browser_bridge.js --urls '["https://...","https://..."]' --out <file>
 *
 * 输出 JSON：
 *   {"ok": true, "results": {"<原始链接>": {"ok": true, "detail": {...}}}}
 *   {"ok": true, "results": {"<原始链接>": {"ok": false, "error": "..."}}}
 *   {"ok": false, "error": "..."}                     ← 整体失败（如浏览器起不来）
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

/**
 * 加载 Playwright。
 *
 * 本脚本位于 backend/app/，而 playwright 装在前端 frontend/node_modules（项目里前端
 * 已经用它做冒烟测试，后端不再重复安装一份）。Node 的 `require` 是按**脚本自身路径**
 * 解析模块的，`cwd` 不参与，所以必须显式从 frontend 目录解析。
 */
function loadPlaywright() {
  const candidates = [
    process.env.FVD_FRONTEND_DIR,
    path.resolve(__dirname, '..', '..', 'frontend'),
  ].filter(Boolean);
  const errors = [];
  for (const dir of candidates) {
    try {
      return createRequire(path.join(dir, 'package.json'))('playwright');
    } catch (exc) {
      errors.push(`${dir}: ${exc.message}`);
    }
  }
  throw new Error(`无法加载 playwright（已尝试 ${errors.join(' | ')}）`);
}

/** 抖音分享短链/各种链接里取数字 aweme_id（与后端 douyin.py 的规则保持一致）。 */
function extractAwemeId(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    return null;
  }
  // 路径里明确写了 /video/<id> 时以路径为准（与后端一致）
  const m = parsed.pathname.match(/\/(?:video|note|share\/video)\/(\d+)/i);
  if (m && /^\d+$/.test(m[1])) return m[1];

  for (const key of ['modal_id', 'aweme_id', 'item_ids', 'vid']) {
    const value = parsed.searchParams.get(key);
    if (value && /^\d+$/.test(value)) return value;
  }
  return null;
}

function parseArgs(argv) {
  const out = { urls: [], outFile: null, timeoutMs: 90000 };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key === '--urls') { out.urls = JSON.parse(value); i += 1; }
    else if (key === '--urls-file') { out.urls = JSON.parse(fs.readFileSync(value, 'utf8')); i += 1; }
    else if (key === '--out') { out.outFile = value; i += 1; }
    else if (key === '--timeout') { out.timeoutMs = Number(value) || out.timeoutMs; i += 1; }
  }
  return out;
}

/** 在已就绪的视频页里反复尝试取详情：secsdk 未就绪时会被 403 拒绝，稍等重试即可。 */
async function fetchDetailWithRetry(page, url, awemeId, budgetMs) {
  const marker = /"aweme_detail"\s*:\s*\{/;
  const deadline = Date.now() + budgetMs;
  let last = '未知错误';
  while (Date.now() < deadline) {
    const res = await page.evaluate(async (target) => {
      try {
        const r = await fetch(target, { credentials: 'include' });
        return { status: r.status, text: await r.text() };
      } catch (exc) {
        return { status: 0, text: String(exc) };
      }
    }, url);
    if (res.status === 200 && marker.test(res.text)) {
      try {
        const detail = JSON.parse(res.text).aweme_detail;
        if (detail && detail.video) return { ok: true, detail };
        return { ok: false, error: '该链接没有可下载的视频（可能是图文、私密或已删除）' };
      } catch (exc) {
        return { ok: false, error: `详情 JSON 解析失败：${exc.message}` };
      }
    }
    last = res.status
      ? `接口返回 HTTP ${res.status} ${String(res.text).slice(0, 120)}`
      : `页内请求失败：${String(res.text).slice(0, 120)}`;
    await page.waitForTimeout(1200);
  }
  return { ok: false, error: `浏览器会话未能通过抖音风控（${last}）`, awemeId };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targets = args.urls
    .map((url) => ({ url, awemeId: extractAwemeId(url) }))
    .filter((item) => item.awemeId);

  const results = {};
  for (const item of args.urls) {
    if (!extractAwemeId(item)) results[item] = { ok: false, error: '无法从链接中解析出视频 ID' };
  }
  if (!targets.length) {
    return finish(args, { ok: true, results });
  }

  let browser;
  try {
    const { firefox } = loadPlaywright();
    browser = await firefox.launch({ headless: true });
    const context = await browser.newContext({
      locale: 'zh-CN',
      viewport: { width: 1280, height: 900 },
    });
    const page = await context.newPage();
    page.setDefaultTimeout(45000);

    for (const { url, awemeId } of targets) {
      const detailUrl = 'https://www.douyin.com/aweme/v1/web/aweme/detail/'
        + `?device_platform=webapp&aid=6383&channel=channel_pc_web&aweme_id=${awemeId}`;
      try {
        // 先加载视频页：页内 secsdk 在此完成初始化并登记本次会话
        await page.goto(`https://www.douyin.com/video/${awemeId}`,
          { waitUntil: 'domcontentloaded', timeout: 60000 });
        await page.waitForTimeout(2500);
        results[url] = await fetchDetailWithRetry(page, detailUrl, awemeId,
          Math.min(args.timeoutMs, 60000));
      } catch (exc) {
        results[url] = { ok: false, error: `浏览器会话失败：${exc.message}` };
      }
    }
  } catch (exc) {
    return finish(args, { ok: false, error: `无法启动无头浏览器：${exc.message}` });
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
  return finish(args, { ok: true, results });
}

function finish(args, payload) {
  const text = JSON.stringify(payload);
  if (args.outFile) {
    fs.mkdirSync(path.dirname(args.outFile), { recursive: true });
    fs.writeFileSync(args.outFile, text, 'utf8');
  } else {
    process.stdout.write(text);
  }
}

main().then(
  () => process.exit(0),
  (exc) => {
    process.stderr.write(`bridge failed: ${exc && exc.stack ? exc.stack : exc}\n`);
    process.exit(1);
  },
);
