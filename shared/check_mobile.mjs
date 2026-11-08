#!/usr/bin/env node
/* check_mobile.mjs — 実ブラウザでの文字の大きさと横のはみ出しの検査（DESIGN.md 5.2・5.4・9.1。決定 2026-11-08 段階3）。
   shiga-hino-plans の tools/check_mobile.mjs（ADR-8 ゲートB）を元に、どのリポジトリの HTML でも動く形にした。

   各ページを幅 360px と 1024px（高さ 800px）で開き、次を確かめる。
     (1) 表示されている文字の入った要素のすべてで、計算された文字の大きさが 14px 以上か
         （SVG の中の文字は、縮小・拡大のあとの大きさで測る）
     (2) ページ全体が横にはみ出していないか（document の scrollWidth が画面の幅 +1px 以下。表の中の横スクロールは対象外）
   開き方：
     - タブ（[role="tab"] と .tabs .tab）があれば、1つずつ押して表示し、そのたびに測る
     - 測る前に、details をすべて開き、aria-expanded="false" のボタン（[role="tab"] を除く）を押して開く
     - canvas の文字は測れない。Chart.js の文字の大きさは check.py の静的検査で見る
   使い方：
     node shared/check_mobile.mjs <HTML ファイル>...
   Playwright はリポジトリに入れない。環境変数 PLAYWRIGHT_MODULE に playwright の index.mjs のパスを指定する
   （無ければ import("playwright")）。CHROMIUM_PATH があれば、そのブラウザを使う。
   Playwright が見つからないときは終了コード 2 で止まる（黙って合格にしない）。
   終了コード：問題が無ければ 0、あれば 1。 */
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { existsSync } from "node:fs";

const MIN_PX = 14;
const WIDTHS = [360, 1024];
const HEIGHT = 800;

const files = process.argv.slice(2);
if (!files.length) {
  console.error("使い方: node shared/check_mobile.mjs <HTML ファイル>...");
  process.exit(2);
}
for (const f of files) {
  if (!existsSync(f)) {
    console.error(`ファイルが無い: ${f}`);
    process.exit(2);
  }
}

let chromium;
try {
  ({ chromium } = await import(process.env.PLAYWRIGHT_MODULE || "playwright"));
} catch (e) {
  console.error("Playwright が見つかりません。npm install --no-save playwright && npx playwright install chromium を実行するか、");
  console.error("PLAYWRIGHT_MODULE に playwright の index.mjs のパスを指定してください。");
  process.exit(2);
}

const launchOpts = process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {};
const browser = await chromium.launch(launchOpts);
let bad = 0;

// ページの中で、details とボタンの折りたたみを開く
const openAll = () => {
  let n = 0;
  document.querySelectorAll("details:not([open])").forEach((d) => { d.open = true; n++; });
  document.querySelectorAll('[aria-expanded="false"]:not([role="tab"])').forEach((b) => {
    if (b.tagName === "BUTTON" || b.getAttribute("role") === "button") { b.click(); n++; }
  });
  return n;
};

// ページの中で、文字の大きさと横のはみ出しを測る
const measure = (MIN_PX) => {
  const out = { min: Infinity, count: 0, small: [], overflow: null };
  const visible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    const b = el.getBoundingClientRect();
    return b.width > 0 && b.height > 0;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const t = walker.currentNode;
    if (!t.nodeValue.trim()) continue;
    const el = t.parentElement;
    if (!el || seen.has(el) || el.closest("script,style,title,noscript,template")) continue;
    seen.add(el);
    if (!visible(el)) continue;
    let px = parseFloat(getComputedStyle(el).fontSize);
    if (el instanceof SVGElement && el.ownerSVGElement) {
      const m = el.getScreenCTM();
      if (m) px = px * Math.hypot(m.a, m.b);
    }
    out.count++;
    if (px < out.min) out.min = px;
    if (px < MIN_PX - 0.05) {
      const cls = el.getAttribute("class");
      out.small.push(`${px.toFixed(2)}px <${el.tagName.toLowerCase()}${cls ? "." + cls.trim().split(/\s+/)[0] : ""}>「${t.nodeValue.trim().slice(0, 16)}」`);
    }
  }
  const sw = document.documentElement.scrollWidth;
  if (sw > window.innerWidth + 1) out.overflow = `${sw}px > ${window.innerWidth}px`;
  return out;
};

for (const file of files) {
  const url = pathToFileURL(resolve(file)).href;
  const errors = [];
  let minSeen = Infinity;
  let elems = 0;
  let states = 0;
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: HEIGHT } });
    const pageErrors = [];
    page.on("pageerror", (e) => pageErrors.push(String(e.message).split("\n")[0]));
    await page.goto(url, { waitUntil: "load" });
    await page.waitForTimeout(300);
    const tabs = await page.$$('[role="tab"], .tabs .tab');
    const n = Math.max(tabs.length, 1);
    for (let i = 0; i < n; i++) {
      const where = tabs.length ? `${width}px タブ${i + 1}` : `${width}px`;
      if (tabs.length) {
        if (!(await tabs[i].isVisible())) continue;
        await tabs[i].click();
        await page.waitForTimeout(250);
      }
      await page.evaluate(openAll);
      await page.waitForTimeout(150);
      const r = await page.evaluate(measure, MIN_PX);
      states++;
      elems += r.count;
      if (r.min < minSeen) minSeen = r.min;
      if (r.small.length) errors.push(`${where}: ${MIN_PX}px 未満の文字 ${r.small.length}件（例 ${r.small.slice(0, 3).join("、")}）`);
      if (r.overflow) errors.push(`${where}: ページが横にはみ出し ${r.overflow}`);
    }
    if (pageErrors.length) console.log(`  [注意] ${width}px: ページのスクリプトの誤り ${pageErrors.length}件（例 ${pageErrors[0]}）`);
    await page.close();
  }
  const status = errors.length ? "NG" : "OK";
  const minText = Number.isFinite(minSeen) ? `${minSeen.toFixed(2)}px` : "なし";
  console.log(`${status}  ${file}  （測った状態 ${states}、文字の要素のべ ${elems}、最小の文字 ${minText}、誤り ${errors.length}）`);
  errors.forEach((e) => console.log(`  [ERROR] ${e}`));
  if (errors.length) bad++;
}

await browser.close();
process.exit(bad ? 1 : 0);
