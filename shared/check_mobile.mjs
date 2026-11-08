#!/usr/bin/env node
/* check_mobile.mjs — 実ブラウザでの文字の大きさと横のはみ出しの検査（DESIGN.md 5.2・5.4・9.1。決定 2026-11-08 段階3）。
   shiga-hino-plans の tools/check_mobile.mjs（ADR-8 ゲートB）を元に、どのリポジトリの HTML でも動く形にした。

   各ページを幅 360px と 1024px（高さ 800px）で開き、次を確かめる。
     (1) 表示されている文字の入った要素のすべてで、計算された文字の大きさが 14px 以上か
         （SVG の中の文字は、縮小・拡大のあとの大きさで測る）
     (2) ページ全体が横にはみ出していないか（document の scrollWidth が画面の幅 +1px 以下。表の中の横スクロールは対象外）
   開き方：
     - ページは file:// では開かず、HTML の親のフォルダをルートにして手元の http（127.0.0.1 の空いた番号）で配って開く。
       ページが fetch や Papa.parse で読む CSV・data.js などを読めるようにするため。CDN からの読み込みは、ページに書いてあればそのまま行う
     - 検査する画面（# のあとの名前で開く画面）を、--hash a,b,c で名前を並べて指定するか、--all-hashes で
       ページの中の a[href^="#"] の名前を集めて順に開く。どちらの場合も、# の無い最初の画面も測る。指定が無ければ # の無い画面だけ
     - タブ（[role="tab"] と .tabs .tab）があれば、1つずつ押して表示し、そのたびに測る
     - 測る前に、details をすべて開き、aria-expanded="false" のボタン（[role="tab"] を除く）を押して開く
     - canvas の文字は測れない。Chart.js の文字の大きさは check.py の静的検査で見る
   使い方：
     node shared/check_mobile.mjs [--hash a,b,c | --all-hashes] <HTML ファイル>...
   出力：画面ごとに、測った要素の数と最小の文字の大きさを出す。最後にファイルごとの合計の1行を出す。
   Playwright はリポジトリに入れない。環境変数 PLAYWRIGHT_MODULE に playwright の index.mjs のパスを指定する
   （無ければ import("playwright")）。CHROMIUM_PATH があれば、そのブラウザを使う。
   Playwright が見つからないときは終了コード 2 で止まる（黙って合格にしない）。
   終了コード：問題が無ければ 0、あれば 1。 */
import { resolve, dirname, basename, extname, join, sep } from "node:path";
import { existsSync, statSync, createReadStream } from "node:fs";
import http from "node:http";

const MIN_PX = 14;
const WIDTHS = [360, 1024];
const HEIGHT = 800;

const USAGE = "使い方: node shared/check_mobile.mjs [--hash a,b,c | --all-hashes] <HTML ファイル>...";
const files = [];
let hashList = null; // --hash の名前の並び
let allHashes = false;
{
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--hash") {
      if (i + 1 >= args.length) { console.error(USAGE); process.exit(2); }
      hashList = args[++i].split(",").map((x) => x.trim().replace(/^#/, "")).filter(Boolean);
    } else if (a.startsWith("--hash=")) {
      hashList = a.slice(7).split(",").map((x) => x.trim().replace(/^#/, "")).filter(Boolean);
    } else if (a === "--all-hashes") {
      allHashes = true;
    } else if (a.startsWith("--")) {
      console.error(`知らない指定: ${a}`); console.error(USAGE); process.exit(2);
    } else {
      files.push(a);
    }
  }
}
if (!files.length || (hashList && allHashes)) {
  console.error(USAGE);
  if (hashList && allHashes) console.error("--hash と --all-hashes は一緒に使えない");
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

// HTML の親のフォルダをルートにして、手元の http で配る（フォルダごとに1つ）
const TYPES = {
  ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".csv": "text/csv; charset=utf-8", ".tsv": "text/tab-separated-values; charset=utf-8", ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
  ".webp": "image/webp", ".ico": "image/x-icon", ".pdf": "application/pdf", ".woff2": "font/woff2",
};
const servers = new Map();
function serve(root) {
  if (servers.has(root)) return servers.get(root);
  const p = new Promise((res, rej) => {
    const s = http.createServer((req, rsp) => {
      let rel;
      try { rel = decodeURIComponent(new URL(req.url, "http://x").pathname); } catch { rsp.writeHead(400); rsp.end(); return; }
      let f = resolve(join(root, rel));
      if (f !== root && !f.startsWith(root + sep)) { rsp.writeHead(403); rsp.end(); return; }
      if (existsSync(f) && statSync(f).isDirectory()) f = join(f, "index.html");
      if (!existsSync(f) || !statSync(f).isFile()) { rsp.writeHead(404); rsp.end(); return; }
      rsp.writeHead(200, { "content-type": TYPES[extname(f).toLowerCase()] || "application/octet-stream" });
      createReadStream(f).pipe(rsp);
    });
    s.on("error", rej);
    s.listen(0, "127.0.0.1", () => res({ server: s, base: `http://127.0.0.1:${s.address().port}` }));
  });
  servers.set(root, p);
  return p;
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

// ページの中の a[href^="#"] の名前を、出てくる順に重ならないように集める（--all-hashes）
const collectHashes = () => {
  const out = [];
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    const h = a.getAttribute("href").slice(1);
    if (h && !out.includes(h)) out.push(h);
  });
  return out;
};

const fmtPx = (v) => (Number.isFinite(v) ? `${v.toFixed(2)}px` : "なし");

for (const file of files) {
  const abs = resolve(file);
  const { base } = await serve(dirname(abs));
  const url = `${base}/${encodeURIComponent(basename(abs))}`;
  const errors = [];
  let minSeen = Infinity;
  let elems = 0;
  let states = 0;
  const screenNames = new Set();
  let screens = 0;
  console.log(`${file}（${url} で開いた）`);
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: HEIGHT } });
    const pageErrors = [];
    page.on("pageerror", (e) => pageErrors.push(String(e.message).split("\n")[0]));
    await page.goto(url, { waitUntil: "load" });
    await page.waitForTimeout(300);
    // 測る画面の並び。"" は # の無い最初の画面
    let hashes = [""];
    if (hashList) hashes = ["", ...hashList.filter((h) => h)];
    if (allHashes) hashes = ["", ...(await page.evaluate(collectHashes))];
    for (const h of hashes) {
      const screen = h ? `#${h}` : "（# なし）";
      if (h) {
        await page.evaluate((x) => { location.hash = x; }, h);
        await page.waitForTimeout(500);
      }
      screens++;
      screenNames.add(screen);
      let sCount = 0;
      let sMin = Infinity;
      let sStates = 0;
      const tabs = await page.$$('[role="tab"], .tabs .tab');
      const n = Math.max(tabs.length, 1);
      for (let i = 0; i < n; i++) {
        const where = `${width}px ${screen}` + (tabs.length ? ` タブ${i + 1}` : "");
        if (tabs.length) {
          if (!(await tabs[i].isVisible())) continue;
          await tabs[i].click();
          await page.waitForTimeout(250);
        }
        await page.evaluate(openAll);
        await page.waitForTimeout(150);
        const r = await page.evaluate(measure, MIN_PX);
        states++; sStates++;
        elems += r.count; sCount += r.count;
        if (r.min < minSeen) minSeen = r.min;
        if (r.min < sMin) sMin = r.min;
        if (r.small.length) errors.push(`${where}: ${MIN_PX}px 未満の文字 ${r.small.length}件（例 ${r.small.slice(0, 3).join("、")}）`);
        if (r.overflow) errors.push(`${where}: ページが横にはみ出し ${r.overflow}`);
      }
      console.log(`  ${width}px ${screen}  （測った状態 ${sStates}、文字の要素 ${sCount}、最小の文字 ${fmtPx(sMin)}）`);
    }
    if (pageErrors.length) console.log(`  [注意] ${width}px: ページのスクリプトの誤り ${pageErrors.length}件（例 ${pageErrors[0]}）`);
    await page.close();
  }
  const status = errors.length ? "NG" : "OK";
  console.log(`${status}  ${file}  （画面 ${screenNames.size}（幅2つで ${screens}）、測った状態 ${states}、文字の要素のべ ${elems}、最小の文字 ${fmtPx(minSeen)}、誤り ${errors.length}）`);
  errors.forEach((e) => console.log(`  [ERROR] ${e}`));
  if (errors.length) bad++;
}

await browser.close();
for (const p of servers.values()) (await p).server.close();
process.exit(bad ? 1 : 0);
