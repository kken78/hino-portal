# 共通の部品（正本）

ポータルの下のページ（計画と予算、統計とくらし）が共通に使う、見出し・分野のナビ・ページの一覧・フッターの正本。DESIGN.md 2章（構造）と 9.1（検査）による。議会系のページ（council-dashboard、hino-council-search）は使わない（8章）。

| ファイル | 中身 | ページでの置き方 |
|---|---|---|
| shell.css | 共通の部品の CSS。クラス名は `portal-` で始まり、ページの CSS とぶつからない | `<head>` の中に `<!-- portal-shared:css start --><style>…</style><!-- portal-shared:css end -->` として写す |
| header.html | 共通の見出し（名前・「非公式」の印・分野のナビ） | `<body>` の最初に `<!-- portal-shared:header start -->…<!-- portal-shared:header end -->` として写す。いまの分野のリンクに `aria-current="page"` を付ける（1つだけ） |
| siblings-plan.html・siblings-stat.html | 分野の中のページの一覧（2.3） | ページの見出しの中（`.portal-page` の最後）に `<!-- portal-shared:siblings start -->…end -->` として写す。いま開いているページは `<a href="…">題</a>` を `<span aria-current="page">題</span>` に替える |
| footer.html | フッターの型（2.5 の7項目） | `<!-- portal-shared:footer start -->…end -->` として置き、`{{…}}` をページの中身に替える。項目の順は変えない。当てはまらない項目（ポータルのトップの「出典」など）は飛ばしてよい。「このページについて」の最初の文と「注意」の文は変えない |
| check.py | 上が正本と同じかと、文字の大きさ（DESIGN.md 5.2）を確かめる静的検査 | 各リポジトリの CI で、hino-portal を浅く取ってきて `python3 hino-portal/shared/check.py <HTML>` を走らせる（下） |
| check_mobile.mjs | 実ブラウザで、文字の実寸が 14px 以上か、ページが横にはみ出さないかを確かめる検査 | 各リポジトリの CI で `node hino-portal/shared/check_mobile.mjs <HTML>` を走らせる（下）。Playwright が要る |

## ページの見出し（2.2 の 2）

共通の見出しの次に置く。型は次のとおり（共通の部品ではないので check.py は見ないが、クラス名は shell.css のもの）。

```html
<div class="portal-page"><div class="portal-wrap">
<p class="portal-area">計画と予算</p>
<h1 class="portal-title">当初予算 主な事業（令和3〜8年度）</h1>
<p class="portal-lead">説明の1行。</p>
<p class="portal-asof">資料の時点：…。転記日：…</p>
<!-- portal-shared:siblings start -->…<!-- portal-shared:siblings end -->
</div></div>
```

ページの題は `h1`（共通の見出しの名前は `h1` にしない）。題の下に「プロトタイプ」などの札は置かない。英語の小見出しは使わない。`<title>` は「ページの題｜日野町データポータル（非公式）」。

## 文字の大きさ（DESIGN.md 5.2・9.1）

文字の大きさは、共通の部品のトークン5つだけを使う。14px より小さい文字は作らない。

| トークン | 値 | 使うところ |
|---|---|---|
| `--portal-fs-sub` | 14px | 付随する情報（フッター、出典、注記、グラフの軸の目盛り） |
| `--portal-fs` | 16px | 本文と操作の部品 |
| `--portal-fs-h1` | 18px | 見出しの1段め |
| `--portal-fs-h3` | 20px | 見出しの2段め |
| `--portal-fs-h2` | 24px | 見出しの3段め（ページの題） |

ページの CSS に自分のトークン（`--fs-*` など）を置くときは、値をこの5つのどれか（`var(--portal-fs-sub)` のような参照か、同じ値）にする。狭い画面の上書きで小さくしない。

check.py の文字の大きさの検査は、shiga-hino-plans の validate.mjs の文字の規則（7）（8）を写したもので、生成物の HTML の中の次を見る。

- 見るもの：`<style>` の中の `font-size:` の宣言、`style` 属性の `font-size`、`font-size="…"` 属性（SVG）、トークン `--fs*`・`--portal-fs*` の定義（`@media` の中の上書きを含む）
- 通る値：トークンの参照 `var(--…)`（参照の先のすべての定義が 14px 以上）、px、rem（1rem＝16px で換算）、`clamp()`（最小値で判定）、SVG の属性の数（px とみなす）で 14px 以上のもの。`inherit`
- 誤りにするもの：14px 未満の値、em・%・`smaller` など親や既定の大きさによる値、`calc()` など判定できない値、`font:` の一括指定に書いた大きさ、`<small>` の要素
- Chart.js を読み込むページ（`src` に chart を含む `<script>` か `new Chart(` があるページ）：`Chart.defaults.font.size` を 14 以上に決めていること（Chart.js の既定は 12px）、`font:{size:N}` の N と canvas の `ctx.font` の px が 14 以上であること
- 見ないもの：ページの外の .js ファイルが実行時に作る文字（実寸の検査で見る）。canvas に描かれた文字の実寸（測れないので、上の Chart.js の項で見る）

`python3 shared/check.py --selftest` で、通る見本1つと通らない見本19（12px の直接の指定、`<small>`、em、%、clamp の最小値が 12px、Chart.js の size:12 など）が見本どおりに判定されるかを確かめられる。

check_mobile.mjs は、shiga-hino-plans の tools/check_mobile.mjs（ゲートB）を元にしたもので、次のように測る。

- 幅 360px と 1024px（高さ 800px）で開く
- タブ（`[role="tab"]` と `.tabs .tab`）があれば1つずつ押して、そのたびに測る。測る前に `details` をすべて開き、`aria-expanded="false"` のボタンを押して開く
- 表示されている文字の入った要素のすべてで、計算された文字の大きさが 14px 以上か（SVG の中の文字は縮小のあとの大きさ）
- ページ全体が横にはみ出していないか（`scrollWidth` が画面の幅 +1px 以下。表の中の横スクロールは対象外）

Playwright はリポジトリに入れない（package.json を増やさない）。環境変数 `PLAYWRIGHT_MODULE` に playwright の `index.mjs` のパスを指定する。指定が無ければ `import("playwright")` で読む。`CHROMIUM_PATH` があれば、そのブラウザを使う。Playwright が見つからないときは終了コード 2 で止まる。

手元で動かすとき（Playwright を入れる場所は、Mac は `~/GitHub/.tools`、Linux は `~/GitHub/hino-portal-work/tools`）：

```sh
PLAYWRIGHT_MODULE=~/GitHub/hino-portal-work/tools/node_modules/playwright/index.mjs \
  node ~/GitHub/hino-portal/shared/check_mobile.mjs index.html
```

## CI での確かめ方

```yaml
- name: 共通の部品と文字の大きさ（hino-portal の shared/check.py）
  run: |
    git clone --depth 1 https://github.com/kken78/hino-portal.git /tmp/hino-portal
    python3 /tmp/hino-portal/shared/check.py index.html

- uses: actions/setup-node@v7
  with:
    node-version: "22"

- name: 実ブラウザでの文字の大きさと横のはみ出し（hino-portal の shared/check_mobile.mjs）
  run: |
    mkdir -p /tmp/pw && cd /tmp/pw
    npm install --no-save --no-package-lock playwright@1.49.1
    npx playwright install --with-deps chromium
    cd "$GITHUB_WORKSPACE"
    PLAYWRIGHT_MODULE=/tmp/pw/node_modules/playwright/index.mjs node /tmp/hino-portal/shared/check_mobile.mjs index.html
```

`index.html` は、そのリポジトリの生成物（shiga-hino-plans は `docs/index.html docs/plans/*.html` など）に替える。生成物がリポジトリに無いもの（hino-council-search の dist/ など）は、作ってから当てる。

## 正本を変えるとき

1. DESIGN.md を先に改め、決定の記録に書く。
2. この正本を変え、hino-portal の index.html を合わせて PR にする。`python3 shared/check.py index.html` と `node shared/check_mobile.mjs index.html` が通ることを確かめる。
3. 各リポジトリで写し直す（各リポジトリの CI が、正本との違いを知らせる）。
