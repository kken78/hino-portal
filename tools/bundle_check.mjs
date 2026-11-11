#!/usr/bin/env node
/* bundle_check.mjs — 手元版の実ブラウザでの検査（DESIGN.md 11.5）。tools/bundle.py から呼ぶ。

   一式の全ページを、実ブラウザ（Chromium）で file:// のまま開き、次を数える。
     - 外への通信（file:・data:・blob: 以外への要求。通さずに止めて数える）
     - JavaScript のエラー（ページの中で捕まえられなかった例外）
     - コンソールのエラー
     - 手元のファイルを読めなかったもの（file: の要求の失敗）
   各ページは load を待ってから 1.5 秒置き、次の順に画面を変えて数える（shared/check_mobile.mjs の --all-hashes と同じ考え方）。
     1. タブ（[role="tab"] と .tabs .tab）を1つずつ押す
     2. ページの中の a[href^="#"] の名前を集め、location.hash に入れて順に開く
   あわせて、次も数える。
     - 印で切れるリンク：幅 1280px と 360px で、タブごとに、「（インターネット）」の印の付くリンク
       （http(s) で始まるもの）のうち、リンクの箱の幅に字が入りきらないもの
     - 帯の行数：幅 360px での上の帯（.temoto-band p）の行数

   使い方：node tools/bundle_check.mjs <ページの一覧の JSON> <結果の JSON>
     ページの一覧の JSON：{"root": 出力先, "pages": [出力先からのパス...], "timeout": 秒}
   Playwright はリポジトリに入れない。環境変数 PLAYWRIGHT_MODULE に playwright の index.mjs のパスを指定する
   （無ければ import("playwright")）。CHROMIUM_PATH があれば、そのブラウザを使う（shared/check_mobile.mjs と同じ）。
   終了コード：数え終えたら 0（問題の有無は結果の JSON で返す）、Playwright が無いときは 2。 */
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const [listPath, outPath] = process.argv.slice(2);
if (!listPath || !outPath) {
  console.error("使い方: node tools/bundle_check.mjs <ページの一覧の JSON> <結果の JSON>");
  process.exit(2);
}
let chromium;
try {
  ({ chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright"));
} catch (e) {
  console.error("Playwright を読み込めません：" + e.message);
  console.error("PLAYWRIGHT_MODULE に playwright の index.mjs のパスを指定してください。");
  process.exit(2);
}
const { root, pages, timeout = 120 } = JSON.parse(readFileSync(listPath, "utf8"));
const launchOpts = process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {};
const browser = await chromium.launch(launchOpts);
const LOCAL = /^(file|data|blob|about):/i;
const TABS = '[role="tab"], .tabs .tab';
// 印の付くリンクで、字が入りきらないもの（見えているものだけ）
const clipped = () => [...document.querySelectorAll('a[href^="http://"], a[href^="https://"], a[href^="//"]')]
  .filter((a) => a.offsetParent && getComputedStyle(a, "::after").content !== "none" && a.scrollWidth > a.clientWidth + 1)
  .map((a) => (a.className ? "." + String(a.className).split(" ")[0] + " " : "") + a.textContent.trim().slice(0, 30));
const bandLines = () => {
  const p = document.querySelector(".temoto-band p");
  if (!p) return 0;
  const cs = getComputedStyle(p);
  const h = p.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  return Math.round(h / parseFloat(cs.lineHeight));
};
const results = [];
for (const page of pages) {
  const r = { page, requests: [], pageErrors: [], consoleErrors: [], failed: [], loadError: null,
    clipped: [], bandLines360: 0, tabs: 0, hashes: 0 };
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: "block" });
  await ctx.route("**/*", (route) => {
    const u = route.request().url();
    if (LOCAL.test(u)) return route.continue();
    r.requests.push(u);
    return route.abort("blockedbyclient");
  });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => r.pageErrors.push(String(e && e.message || e)));
  p.on("console", (m) => { if (m.type() === "error") r.consoleErrors.push(m.text()); });
  p.on("requestfailed", (q) => {
    const u = q.url();
    if (/^file:/i.test(u)) r.failed.push(decodeURI(u) + "（" + (q.failure() && q.failure().errorText) + "）");
  });
  p.on("websocket", (w) => r.requests.push(w.url()));
  const url = pathToFileURL(join(root, page)).href;
  const t0 = Date.now();
  try {
    await p.goto(url, { waitUntil: "load", timeout: timeout * 1000 });
    await p.waitForTimeout(1500);
    const docUrl = p.url().split("#")[0];
    const back = async () => {  // タブを押してほかのファイルへ移ったときは戻す
      if (p.url().split("#")[0] !== docUrl) await p.goto(url, { waitUntil: "load", timeout: timeout * 1000 });
    };
    const clipAt = async (label) => {
      for (const w of [1280, 360]) {
        await p.setViewportSize({ width: w, height: 900 });
        await p.waitForTimeout(100);
        for (const c of await p.evaluate(clipped)) {
          const k = `幅 ${w}px ${label}：${c}`;
          if (!r.clipped.includes(k)) r.clipped.push(k);
        }
        if (w === 360) r.bandLines360 = Math.max(r.bandLines360, await p.evaluate(bandLines));
      }
      await p.setViewportSize({ width: 1280, height: 900 });
    };
    await clipAt("最初の画面");
    const nTabs = (await p.$$(TABS)).length;
    for (let i = 0; i < nTabs; i++) {
      const tabs = await p.$$(TABS);
      if (!tabs[i] || !(await tabs[i].isVisible())) continue;
      await tabs[i].click();
      await p.waitForTimeout(250);
      r.tabs++;
      await back();
      await clipAt(`タブ${i + 1}`);
    }
    const hashes = await p.evaluate(() => [...new Set([...document.querySelectorAll('a[href^="#"]')]
      .map((a) => a.getAttribute("href").slice(1)).filter(Boolean))]);
    for (const h of hashes) {
      await p.evaluate((x) => { location.hash = x; }, h);
      await p.waitForTimeout(150);
      r.hashes++;
    }
    await back();
  } catch (e) {
    r.loadError = String(e.message || e).split("\n")[0];
  }
  // 止めた外への要求は、コンソールにも「読み込めなかった」として出る。外への通信として数えたものは重ねて数えない
  if (r.requests.length) r.consoleErrors = r.consoleErrors.filter((m) => !/ERR_BLOCKED_BY_CLIENT/.test(m));
  const sec = ((Date.now() - t0) / 1000).toFixed(1);
  const n = r.requests.length + r.pageErrors.length + r.consoleErrors.length + r.failed.length + (r.loadError ? 1 : 0)
    + r.clipped.length;
  console.log(`  ${n ? "問題" : "OK"}  ${page}（タブ ${r.tabs}、# の画面 ${r.hashes}、帯 ${r.bandLines360} 行、${sec} 秒）`);
  results.push(r);
  await ctx.close();
}
await browser.close();
writeFileSync(outPath, JSON.stringify(results, null, 1));
