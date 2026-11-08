# 共通の部品（正本）

ポータルの下のページ（計画と予算、統計とくらし）が共通に使う、見出し・分野のナビ・ページの一覧・フッターの正本。DESIGN.md 2章（構造）と 9.1（検査）による。議会系のページ（council-dashboard、hino-council-search）は使わない（8章）。

| ファイル | 中身 | ページでの置き方 |
|---|---|---|
| shell.css | 共通の部品の CSS。クラス名は `portal-` で始まり、ページの CSS とぶつからない | `<head>` の中に `<!-- portal-shared:css start --><style>…</style><!-- portal-shared:css end -->` として写す |
| header.html | 共通の見出し（名前・「非公式」の印・分野のナビ） | `<body>` の最初に `<!-- portal-shared:header start -->…<!-- portal-shared:header end -->` として写す。いまの分野のリンクに `aria-current="page"` を付ける（1つだけ） |
| siblings-plan.html・siblings-stat.html | 分野の中のページの一覧（2.3） | ページの見出しの中（`.portal-page` の最後）に `<!-- portal-shared:siblings start -->…end -->` として写す。いま開いているページは `<a href="…">題</a>` を `<span aria-current="page">題</span>` に替える |
| footer.html | フッターの型（2.5 の7項目） | `<!-- portal-shared:footer start -->…end -->` として置き、`{{…}}` をページの中身に替える。項目の順は変えない。当てはまらない項目（ポータルのトップの「出典」など）は飛ばしてよい。「このページについて」の最初の文と「注意」の文は変えない |
| check.py | 上が正本と同じかと、文字の大きさ（DESIGN.md 5.2）・表記・太さ・外部からの読み込みを確かめる静的検査 | 各リポジトリの CI で、hino-portal を浅く取ってきて `python3 hino-portal/shared/check.py <HTML>` を走らせる（下）。共通の部品を持たない議会系のページは `--no-shared` を付ける |
| apply.py | 各ページの共通の部品のブロックを、正本で置き換える道具（DESIGN.md 9.2） | 各リポジトリで `python3 <hino-portal>/shared/apply.py <HTML>` を走らせ、書き換えたものをそのリポジトリでコミットする（下の「共通の部品を写す」） |
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

check.py は、`lang`・`<title>` の形・共通の部品の写し・文字の大きさのすべてを既定で確かめる。文字の大きさの検査は、段階3 のあいだは `--fonts` を付けたときだけ行っていたが、9つのリポジトリで段階3 の PR が出そろったので既定にした（2026-11-08）。`--fonts` は互換のために残してあり、付けても付けなくても同じ動きになる。各リポジトリの CI の `--fonts` は外さなくてよい。

共通の部品を持たないページ（議会系の council-dashboard・hino-council-search。DESIGN.md 8章）では `--no-shared` を付ける。`<title>` の形と、共通の部品の4つのブロック（css・header・siblings・footer）の検査を外し、`lang` と文字の大きさだけを確かめる。

check.py の文字の大きさの検査は、shiga-hino-plans の validate.mjs の文字の規則（7）（8）を写したもので、生成物の HTML の中の次を見る。

- 見るもの：`<style>` の中の `font-size:` の宣言、`style` 属性の `font-size`、`font-size="…"` 属性（SVG）、トークン `--fs*`・`--portal-fs*` の定義（`@media` の中の上書きを含む）
- 通る値：トークンの参照 `var(--…)`（参照の先のすべての定義が 14px 以上）、px、rem（1rem＝16px で換算）、`clamp()`（最小値で判定）、SVG の属性の数（px とみなす）で 14px 以上のもの。`inherit`
- 誤りにするもの：14px 未満の値、em・%・`smaller` など親や既定の大きさによる値、`calc()` など判定できない値、`font:` の一括指定に書いた大きさ、`<small>` の要素
- Chart.js を読み込むページ（`src` に chart を含む `<script>` か `new Chart(` があるページ）：`Chart.defaults.font.size` を 14 以上に決めていること（Chart.js の既定は 12px）、`font:{size:N}` の N と canvas の `ctx.font` の px が 14 以上であること
- 見ないもの：ページの外の .js ファイルが実行時に作る文字（実寸の検査で見る）。canvas に描かれた文字の実寸（測れないので、上の Chart.js の項で見る）

`python3 shared/check.py --selftest` で、見本63件が見本どおりに判定されるかを確かめられる。内訳は、文字の大きさの通る見本1つと通らない見本19（12px の直接の指定、`<small>`、em、%、clamp の最小値が 12px、Chart.js の size:12 など）、表記・太さ・外部からの読み込みの通る見本1つと通らない見本28（下）、指定の見本14（指定が無くても `--fonts` でも文字の検査が動くこと、`--no-shared` で `<title>` の形と共通の部品の検査が外れ、文字の検査は残ること、`--hyoki` で表記と太さの検査が加わること、外部からの読み込みが既定は警告で `--strict-external` では誤りになること）。

## 表記・太さ・外部からの読み込み（DESIGN.md 3.3・4.2・5.2・5.6・6.4・9.1）

check.py は、次の3つも見る。表記と太さは、各リポジトリの段階4 の PR が出そろうまでは `--hyoki` を付けたときだけ行う（いま既定にすると、各リポジトリの CI が落ちるため。出そろったら既定にし、`--hyoki` は互換の指定として残す。文字の大きさの `--fonts` と同じ形）。外部からの読み込みは既定で行い、警告にとどめる。

表記（`--hyoki`）。見るのは本文の文字で、`<script>`・`<style>` の中と HTML のコメントは除き、`alt`・`aria-label`・`title` 属性の字は含める。段落・表のセル・項目などの要素の境目は区切りとして扱い、隣の要素の字とつなげない。

| 項目 | 誤りにするもの | 通るもの |
|---|---|---|
| 増減の印（3.3） | 「▲」「▼」「↑」「↓」の直後（空白をはさんでもよい）に数字か「増」「減」があるもの（「▲1,531」「▲ 増」「↑12人」） | 原典の字の引用で、直後が数字・増・減でないもの（「原典の表では▲を負の値の印に使っている」） |
| +（6.4） | 「+」「＋」の直後に数字があるもの（「+80人」） | URL の中、`<code>`・`<pre>` の中 |
| リンクの文と比べ方（5.6・6.2） | 「くわしく」「こちら」「前年比」「前年度比」「前回比」 | |
| 新しいタブ（5.6） | `target="_blank"` の `<a>` で、「新しいタブで開きます」の字が、要素の中の文字にも、`aria-label`・`title` にも、中の要素の `alt`・`aria-label`・`title` にも無いもの | |
| R の注（6.4） | 「R」＋数字＋（年・年度・.・〜）の形（「R7年度」「R8.3」「R3〜R8」）があるのに、「R＝令和」か「R は令和」の字が無いページ | |

太さ（`--hyoki`。5.2）。`<style>` の `font-weight`、`style` 属性の `font-weight`、`font:` の一括指定の太さが、400・700・normal・bold・inherit・800 のどれかであること。800 は数字の札の主の値にだけ認めるが、どの要素かは静的には決められないので通す。500・600・900・`bolder`・`lighter` と、そのほかの値（100〜300 など）を誤りにする。`var(--…)` は、ページの中の定義をすべてたどって判定する。

外部からの読み込み（4.2）。`<script src>`、`<link href>`（`rel` が canonical・alternate のものは読み込まないので除く）、`@import`、`url(…)`（`<style>` と `style` 属性）、`<img src>` で、`http://`・`https://`・`//` で始まるもの。GitHub・町のサイトへの `<a href>` は見ない。既定は警告で、終了コードを変えない。警告は「  警告：」で始まる行に出す（各リポジトリの CI には「  - 」で始まる行を問題として数えるものがあるため、その形にしない）。`--strict-external` を付けると誤りにする。日野のすがた・チョイソコひの の CDN を段階5 で同梱に替えたあとに、各リポジトリの CI に付ける。

見ないもの：ページの JavaScript が実行時に作る文字とリンク（グラフの軸の「R7」、あとから足す `target="_blank"` など）。段階4 で直すときは、画面で確かめる。

```sh
python3 ~/GitHub/hino-portal/shared/check.py --hyoki index.html
python3 ~/GitHub/hino-portal/shared/check.py --hyoki --no-shared docs/index.html   # 議会系のページ
```

## 共通の部品を写す（DESIGN.md 9.2）

`shared/apply.py` は、ページの `<!-- portal-shared:〈名前〉 start -->` … `<!-- portal-shared:〈名前〉 end -->` の中を、このフォルダの正本で置き換える。正本を変えたあと、各リポジトリで写し直すときに使う。

| 名前 | 正本 | 置き換えたあとも保つもの |
|---|---|---|
| css | shell.css（`<style>` と `</style>` の間に、そのまま入れる） | |
| header | header.html | 分野のナビの `aria-current="page"`（いまの分野のリンクの文字と href で探して、同じリンクに付け直す） |
| siblings | siblings-plan.html か siblings-stat.html（いまのブロックの `aria-label` で選ぶ） | いまのページの `<span aria-current="page">題</span>` |
| siblings-plan・siblings-stat | siblings-plan.html・siblings-stat.html | 同上 |
| footer | footer.html | `{{…}}` を埋めた中身。項目（dt）ごとにページの dd を残し、dd の先頭の固定の文（「このページについて」の位置づけの文、「注意」の固定の文）だけを正本の字にする。項目の順は正本の順にそろえ、ページに無い項目は足さない |

- 正本と同じブロック（check.py と同じ比べ方。空白の違いは見ない）は書き換えない。ブロックの前後の空白と改行は元のものを保つ。
- いまの分野やいまのページが正本に無いなど、元の値を保てないファイルは、書き換えずに理由を出す（終了コード 2）。
- 終了コードは、書き換えたファイルがあってもなくても 0（書き換えたファイルの一覧を出す）。`--check` を付けると書き換えずに違うブロックの一覧だけを出し、違いがあれば 1。
- 写したものをコミットするのは各リポジトリ。書き換えたら、そのリポジトリの手順で check.py と check_mobile.mjs を通す。shiga-hino-plans は、正本の写しをファイルのまま `templates/portal/` に置いて生成物を作るので、apply.py ではなくそのファイルを写し直して作り直す（生成物に apply.py を当てると、次の生成で元に戻る）。

```sh
python3 ~/GitHub/hino-portal/shared/apply.py --check index.html   # 違いの一覧だけ
python3 ~/GitHub/hino-portal/shared/apply.py index.html           # 書き換える
```

check_mobile.mjs は、shiga-hino-plans の tools/check_mobile.mjs（ゲートB）を元にしたもので、次のように測る。

- ページは `file://` では開かず、HTML の親のフォルダをルートにして手元の http（127.0.0.1）で配って開く。ページが読む CSV や data.js を読めるようにするため。CDN からの読み込みはページに書いてあるとおりに行う（CI は CDN に出られる）。ルートより上のフォルダ（`../`）のファイルは配らない
- 幅 360px と 1024px（高さ 800px）で開く
- `#〈名前〉` で開く画面を持つページは、`--hash a,b,c` で名前を並べて指定するか、`--all-hashes` でページの中の `a[href^="#"]` の名前を集めて順に開く。どちらも、`#` の無い最初の画面も測る。指定が無ければ `#` の無い画面だけを測る
- タブ（`[role="tab"]` と `.tabs .tab`）があれば1つずつ押して、そのたびに測る。測る前に `details` をすべて開き、`aria-expanded="false"` のボタンを押して開く
- 表示されている文字の入った要素のすべてで、計算された文字の大きさが 14px 以上か（SVG の中の文字は縮小のあとの大きさ）
- ページ全体が横にはみ出していないか（`scrollWidth` が画面の幅 +1px 以下。表の中の横スクロールは対象外）
- 画面ごとに、測った文字の要素の数と最小の文字の大きさを出し、最後にファイルごとの合計を1行で出す

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

共通の部品を持たない議会系のページでは、check.py に `--no-shared` を付ける。check.py の出力から共通の部品の問題を grep で除く書き方は要らなくなる。

```yaml
    python3 /tmp/hino-portal/shared/check.py --no-shared docs/index.html
```

`#〈名前〉` で開く画面を持つページ（hino-dashboard など）では、check_mobile.mjs に `--all-hashes` か `--hash` を付ける。

```yaml
    PLAYWRIGHT_MODULE=/tmp/pw/node_modules/playwright/index.mjs node /tmp/hino-portal/shared/check_mobile.mjs --all-hashes index.html
    # 画面を名前で選ぶとき
    PLAYWRIGHT_MODULE=/tmp/pw/node_modules/playwright/index.mjs node /tmp/hino-portal/shared/check_mobile.mjs --hash vital_stats,bus index.html
```

各リポジトリの CI にいま書いてある `--fonts` は、付けたままでも同じに動くので、外す直しは要らない。

## 正本を変えるとき

1. DESIGN.md を先に改め、決定の記録に書く。
2. この正本を変え、hino-portal の index.html を合わせて PR にする。`python3 shared/check.py index.html` と `node shared/check_mobile.mjs index.html` が通ることを確かめる。
3. 各リポジトリで写し直す（`shared/apply.py`。各リポジトリの CI が、正本との違いを知らせる）。
