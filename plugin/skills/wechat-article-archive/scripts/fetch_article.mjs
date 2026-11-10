#!/usr/bin/env node
// 用带调试端口的真实 Chrome 打开公众号文章，取渲染后的正文与元信息。
//
// 为什么要绕这一道：mp.weixin.qq.com 对非浏览器访问（curl / defuddle / WebFetch /
// 无头 Chrome）一律返回「环境异常」验证页，取到的正文是空壳——只剩
// 「视频 小程序 赞 在看」这类零散字样。带调试端口的真实 Chrome 能过这层校验。
//
// 用法：
//   node fetch_article.mjs <url> <输出目录> [--port 9222] [--timeout 90] [--headless]
//
// 产物（写在输出目录里）：
//   article.content.html   #js_content 的渲染后 HTML，交给 wechat_to_md.py
//   article.meta.json     标题、公众号、作者、发布时间
//
// 退出码：0 拿到正文；2 只拿到验证页（窗口里人工过一下验证后重跑）；1 出错。

import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { homedir, platform } from 'node:os';
import { join } from 'node:path';

const argv = process.argv.slice(2);
const VALUE_FLAGS = new Set(['--port', '--timeout']);
const flag = (name, fallback) => {
  const i = argv.indexOf(`--${name}`);
  return i === -1 ? fallback : argv[i + 1];
};
const has = (name) => argv.includes(`--${name}`);

// 位置参数 = 既不是 --flag，也不是某个 --flag 后面跟的值
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (VALUE_FLAGS.has(argv[i])) { i++; continue; }
  if (argv[i].startsWith('--')) continue;
  positional.push(argv[i]);
}
const [rawUrl, outDir] = positional;
if (!rawUrl || !outDir) {
  console.error('用法：node fetch_article.mjs <url> <输出目录> [--port 9222] [--timeout 90] [--headless]');
  process.exit(1);
}

const port = flag('port', '9222');
const timeoutSec = Number(flag('timeout', '90'));
const headless = has('headless');
const base = `http://127.0.0.1:${port}`;

// poc_token 是会过期的临时通行证，归档要存规范链接（biz/mid/idx/sn 那四个参数）
const url = (() => {
  const u = new URL(rawUrl);
  u.searchParams.delete('poc_token');
  u.searchParams.delete('scene');
  return u.toString();
})();

// 专用 profile：登录态与校验 Cookie 跨次复用。别用日常主 Chrome 的 profile，
// 那边通常已经开着，抢不到调试端口。
const profileDir =
  process.env.WECHAT_ARCHIVE_PROFILE ||
  join(process.env.LOCALAPPDATA || homedir(), 'wechat-article-archive', 'chrome-profile');

function chromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = {
    win32: [
      'C:/Program Files/Google/Chrome/Application/chrome.exe',
      'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
      join(process.env.LOCALAPPDATA || '', 'Google/Chrome/Application/chrome.exe'),
      'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
      'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    ],
    darwin: [
      '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
      '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    ],
    linux: ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'],
  }[platform()] || [];
  return candidates.find((p) => p && existsSync(p));
}

async function cdpUp() {
  try {
    const r = await fetch(`${base}/json/version`, { signal: AbortSignal.timeout(2000) });
    return r.ok;
  } catch {
    return false;
  }
}

async function ensureChrome() {
  if (await cdpUp()) return 'reused';
  const bin = chromePath();
  if (!bin) throw new Error('找不到 Chrome/Edge，可用 CHROME_PATH 环境变量指定');
  mkdirSync(profileDir, { recursive: true });
  const args = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    '--no-first-run',
    '--no-default-browser-check',
    ...(headless ? ['--headless=new'] : []),
    'about:blank',
  ];
  spawn(bin, args, { detached: true, stdio: 'ignore' }).unref();
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (await cdpUp()) return 'launched';
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error('Chrome 起来了但调试端口没响应');
}

// ---- 极简 CDP 客户端（Node 18+ 自带 WebSocket 与 fetch，不装依赖）----
async function connect(targetUrl) {
  const ws = new WebSocket(targetUrl);
  let nextId = 1;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    }
  });
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', () => reject(new Error('连不上调试端口')), { once: true });
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  await send('Runtime.enable');
  const evalJs = async (expression) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    return r.result?.value;
  };
  return { ws, send, evalJs };
}

const PROBE = `JSON.stringify({
  ready: (document.querySelector('#js_content')?.innerText || '').trim().length,
  verify: /环境异常|去验证|secitptpage/.test(document.documentElement.outerHTML.slice(0, 20000)),
  url: location.href
})`;

async function main() {
  const how = await ensureChrome();
  const tabs = await (await fetch(`${base}/json/list`)).json();
  let page = tabs.find((t) => t.type === 'page');
  if (!page) {
    await fetch(`${base}/json/new?about:blank`, { method: 'PUT' });
    page = (await (await fetch(`${base}/json/list`)).json()).find((t) => t.type === 'page');
  }
  if (!page) throw new Error('没有可用的标签页');

  const { ws, send, evalJs } = await connect(page.webSocketDebuggerUrl);
  await send('Page.enable');
  await send('Page.navigate', { url });

  // 正文是加载后再渲染的，且验证页要靠人工过，所以轮询到出来为止
  const deadline = Date.now() + timeoutSec * 1000;
  let last = { ready: 0, verify: false, url };
  let verifySince = 0;
  let announced = false;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 1000));
    try {
      last = JSON.parse(await evalJs(PROBE));
    } catch {
      continue; // 导航途中执行上下文会被销毁，属正常
    }
    if (last.ready > 200) break;
    // 有的账号验证页会自己跳走（profile 里的 Cookie 还有效），等一会儿再喊人，
    // 否则每次都要先看到一句吓人的提示
    if (last.verify) {
      verifySince ||= Date.now();
      if (!announced && Date.now() - verifySince > 10000) {
        announced = true;
        console.error('页面停在「环境异常」验证。Chrome 窗口已打开，请在里面手动过一下验证，脚本会继续等。');
      }
    } else {
      verifySince = 0;
    }
  }

  mkdirSync(outDir, { recursive: true });

  if (last.ready <= 200) {
    const html = await evalJs('document.documentElement.outerHTML').catch(() => '');
    const dump = join(outDir, 'article.failed-page.html');
    writeFileSync(dump, html || '', 'utf8');
    console.error(`等了 ${timeoutSec} 秒仍没拿到正文（当前页面 ${last.url}）。`);
    console.error(`把整页存到了 ${dump}——从它可以看出是卡在验证，还是链接已失效（被删、参数错）。`);
    ws.close();
    process.exit(2);
  }

  const meta = await evalJs(`JSON.stringify({
    title: (document.querySelector('#activity-name')?.textContent || '').trim(),
    account: (document.querySelector('#js_name')?.textContent || '').trim(),
    author: (document.querySelector('#js_author_name')?.textContent || '').trim(),
    publishTime: (document.querySelector('#publish_time')?.textContent || '').trim(),
    msgTitle: window.msg_title || '',
    createTime: window.ct || ''
  })`);
  const contentHtml = await evalJs(`document.querySelector('#js_content').outerHTML`);

  writeFileSync(join(outDir, 'article.content.html'), contentHtml, 'utf8');
  writeFileSync(join(outDir, 'article.meta.json'), meta, 'utf8');
  console.log(meta);
  console.log(`Chrome: ${how} | 正文 HTML ${contentHtml.length} 字节 -> ${join(outDir, 'article.content.html')}`);
  ws.close();
  process.exit(0);
}

main().catch((e) => {
  console.error('失败：', e.message);
  process.exit(1);
});
