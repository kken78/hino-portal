# 日野町データポータル（非公式）

https://kken78.github.io/hino-portal/

滋賀県日野町のホームページで公開されている計画・議会の記録・統計をもとにしたダッシュボードの入口ページです。各ダッシュボードはそれぞれ別のリポジトリで公開しています。

| 分野 | ダッシュボード | リポジトリ |
|---|---|---|
| 計画と予算 | 計画ライブラリ | [shiga-hino-plans](https://github.com/kken78/shiga-hino-plans) |
| 計画と予算 | 第6次総合計画 指標と事業費 | [hino-plan-dashboard](https://github.com/kken78/hino-plan-dashboard) |
| 計画と予算 | 予算と決算 町の財政 | [hino-zaisei](https://github.com/kken78/hino-zaisei) |
| 計画と予算 | 固定資産台帳 町の資産 | [hino-shisan](https://github.com/kken78/hino-shisan) |
| 議会 | 議会だより・一般質問 | [council-dashboard](https://github.com/kken78/council-dashboard) |
| 議会 | 会議録 横断検索 | [hino-council-search](https://github.com/kken78/hino-council-search) |
| 統計・くらし | 地区別人口 | [hino-population](https://github.com/kken78/hino-population) |
| 統計・くらし | 日野のすがた | [hino-dashboard](https://github.com/kken78/hino-dashboard) |
| 統計・くらし | チョイソコひの 利用状況 | [choisoko-hino-dashboard](https://github.com/kken78/choisoko-hino-dashboard) |
| 資料 | 町の資料の検索 | [hino-shiryo](https://github.com/kken78/hino-shiryo) |

## 構成

- ポータルと各ダッシュボードに共通する決まり（ページの構造・色・グラフ・文字・文体など）は [DESIGN.md](DESIGN.md) に書いています。
- `index.html` だけで動きます。外部の CSS・JavaScript・フォントは読み込みません。
- 共通の部品（見出し・分野のナビ・ページの一覧・フッター）の正本は `shared/` にあります。各ダッシュボードはこれを写し、CI で `shared/check.py` により正本と同じかと文字の大きさ（`--hyoki` を付けると表記と太さも。外部からの読み込みは警告）を、`shared/check_mobile.mjs` により実ブラウザでの文字の実寸と横のはみ出しを確かめます（置き方は `shared/README.md`、決まりは DESIGN.md 2章・5.2・9.1）。正本を変えたあとに各ページへ写すときは `shared/apply.py` を使います。
- カードのリンクの URL は `index.html` 末尾の `SITES` で管理しています。

ダッシュボードを追加したときは、該当する分野の `<div class="cards">` にカードを1つ足し、この README の表にも1行足してください。「計画と予算」は小見出し（計画・財政）ごとに `<div class="cards two">` があり、カードの題は `h4` です（小見出しが `h3`）。ほかの分野のカードの題は `h3` です。

## OGP 画像の作り直し方

SNS で共有したときに出る画像は `og.png`（1200×630）です。編集元は `assets/og.svg` です。`tools/og_gen.py` は、ポータルと各ダッシュボードの計9本の OGP 画像の編集元を作るスクリプトで、各リポジトリの画像はここで作ったものを使っています。

1. `tools/og_gen.py` の `SITES` の文言や数字を直す。
2. `python3 tools/og_gen.py` を実行する。`tools/out/` にリポジトリ名ごとの svg が9本できる（`tools/out/` はリポジトリに含めない）。
3. `tools/out/` の svg を、Noto Sans CJK JP を入れた環境で 1200×630 の PNG に書き出す。
4. このリポジトリの分は `tools/out/hino-portal.svg` を `assets/og.svg` に、書き出した PNG を `og.png` に置き換える。他のリポジトリの分は、それぞれのリポジトリの og.svg と og.png を置き換える。

## 手元版の作り方

インターネットにつながらない環境で使う一式（手元版。決まりは DESIGN.md 11章）は、`tools/bundle.py` で作ります。各リポジトリの公開しているページを、`bundle.lock.json` に書いた版で束ね、リンクを一式の中への相対のリンクに書き換え、各ページの上に手元版の帯を入れます。あわせて、計画の原典、町の資料、会議録の PDF、議会だより、議員の写真のうち手元にあるものを一式に写し、その URL へのリンクを手元のファイルに向けます。各リポジトリのファイルは変えません。

要るもの：Python 3（標準ライブラリだけ）、git、Node.js（会議録 横断検索を作るのと、会議録の PDF を取るのと、実ブラウザでの検査に使う）、Playwright（置き方は `shared/README.md`）。

1. 各リポジトリを同じフォルダに取り出す（既定は hino-portal の親のフォルダ。ほかの場所なら `--src` で指定する）。すでにあるものは取り出し直さない。

```sh
cd /home/kken78/GitHub
for r in shiga-hino-plans hino-plan-dashboard hino-zaisei hino-shisan hino-population hino-dashboard choisoko-hino-dashboard council-dashboard hino-shiryo hino-council-search hino-town-docs; do
  [ -d $r ] || git clone --depth 1 https://github.com/kken78/$r
done
```

2. 原典をそろえる。道具は次の場所から読みます。

| 原典 | 読み込み元（既定） | 置き方 | 一覧 | 指定 |
|---|---|---|---|---|
| 計画の原典 | `/home/kken78/GitHub/shiga-hino-plans/sources_raw/` | `<id>/<file>` | `data/sources_index.tsv`（lock の版）の file のある行 | `--plans-raw` |
| 町の資料 | `/home/kken78/GitHub/hino-town-docs/sources_raw/` | `<id>.<拡張子>` | `data/sources.tsv`（取り出しのいまの版）の format が pdf・xlsx の行 | `--docs-raw` |
| 会議録 | `/home/kken78/GitHub/hino-council-search/議事録本体/` | `<会議ID>_<ファイル名>` | `public/data/meetings.json`・`toc.json`（lock の版） | `--council-pdf` |
| 議会だより・議員の写真 | `/home/kken78/GitHub/temoto-town-files/` | `議会だより/<ファイル名>`・`写真/<ファイル名>` | council-dashboard の `data/issue-*.json`・`config.json`（lock の版） | `--town-files` |

計画の原典と町の資料は、各リポジトリで取り込んだときに `sources_raw/` に置いたものを使います（shiga-hino-plans の CLAUDE.md、hino-town-docs の DOCS_SCHEMA.md §6）。会議録の PDF は、hino-council-search の README のとおりに取ります。

```sh
cd /home/kken78/GitHub/hino-council-search && node scripts/fetch-pdfs.mjs
```

議会だよりと議員の写真は、次の 3 で `--fetch` を付けると、置き場所に無いものを道具が町のホームページから取ります（1秒に1件。取ったものは置き場所に残り、次からは取り直しません）。

3. 束ねる。出力先と置き場所はリポジトリの外にする。

```sh
PLAYWRIGHT_MODULE=/home/kken78/GitHub/hino-portal-work/tools/node_modules/playwright/index.mjs \
  python3 /home/kken78/GitHub/hino-portal/tools/bundle.py --out /home/kken78/temoto --fetch
```

出力先に `日野町データポータル_手元版/` と `日野町議会_会議録検索/` ができます。原典は `日野町データポータル_手元版/原典/`（`計画/<id>/<file>`、`資料/<分類>/<id>.<拡張子>`、`議会だより/`）、議員の写真は `council-dashboard/写真/`、会議録の PDF は `日野町議会_会議録検索/議事録本体/` に入ります。町の資料の一覧は `資料の一覧.csv` です。前に作ったものがあるときは `--replace` を付けると消して作り直します。作った日は既定で今日で、`--date 2026-11-11` で指定できます。

- 手元に無い原典・会議録・議会だより・写真があると、種類ごとの件数と例を出して止まります。無いものを飛ばして作るときは `--allow-missing` を付けます。飛ばしたものへのリンクは町のホームページの URL のままで、「はじめにお読みください.txt」に入れた件数と入れていない件数が出ます。
- 計画の原典と町の資料は、写すときに sha256 を一覧と比べます。合わないものがあると、一覧を出して止まります。合わないものを入れずに続けるときは `--on-mismatch skip` を付けます。
- 原典の大きさは、一覧の bytes の合計で、計画の原典 764,442,301 バイト、町の資料 2,136,467,869 バイトです（会議録、議会だより、写真の大きさは一覧に無い）。

4. 終わりに渡す前の検査（DESIGN.md 11.5）の結果が出ます。終了コードは、すべて通れば 0、問題があれば 1、作れなかったとき（版が手元に無い、原典が手元に無いなど）は 2、実ブラウザの検査をしなかったとき（`--no-browser` か Playwright が無い）は 3 です。議員の写真を入れずに作ったときは、「議員別」のタブが町のホームページの写真を読む通信が外への通信として数えられ、終了コード 1 になります。作った一式の検査だけをやり直すときは `--check-only` を付けます。

```sh
PLAYWRIGHT_MODULE=/home/kken78/GitHub/hino-portal-work/tools/node_modules/playwright/index.mjs \
  python3 /home/kken78/GitHub/hino-portal/tools/bundle.py --out /home/kken78/temoto --check-only
```

版を上げるときは、`bundle.lock.json` の各リポジトリの `commit` を直す PR を出します。手元の取り出しにその版が無いときは、道具が止まって取ってくるコマンドを出します。

道具の試験：

```sh
cd /home/kken78/GitHub/hino-portal && python3 -m unittest discover -s tools -p 'test_*.py'
```

## ライセンス

コードは MIT License です（[LICENSE](LICENSE)）。
