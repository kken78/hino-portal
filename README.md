# 日野町データポータル（非公式）

https://kken78.github.io/hino-portal/

滋賀県日野町のホームページで公開されている計画・議会の記録・統計をもとにしたダッシュボードの入口ページです。各ダッシュボードはそれぞれ別のリポジトリで公開しています。

| 分野 | ダッシュボード | リポジトリ |
|---|---|---|
| 計画と予算 | 計画ライブラリ | [shiga-hino-plans](https://github.com/kken78/shiga-hino-plans) |
| 計画と予算 | 第6次総合計画 指標と事業費 | [hino-plan-dashboard](https://github.com/kken78/hino-plan-dashboard) |
| 計画と予算 | 当初予算 主な事業（令和3〜8年度） | [hino-budget](https://github.com/kken78/hino-budget) |
| 議会 | 議会だより・一般質問 | [council-dashboard](https://github.com/kken78/council-dashboard) |
| 議会 | 会議録 横断検索 | [hino-council-search](https://github.com/kken78/hino-council-search) |
| 統計・くらし | 地区別人口 | [hino-population](https://github.com/kken78/hino-population) |
| 統計・くらし | 日野のすがた | [hino-dashboard](https://github.com/kken78/hino-dashboard) |
| 統計・くらし | チョイソコひの 利用状況 | [choisoko-hino-dashboard](https://github.com/kken78/choisoko-hino-dashboard) |

## 構成

- ポータルと各ダッシュボードに共通する決まり（ページの構造・色・グラフ・文字・文体など）は [DESIGN.md](DESIGN.md) に書いています。
- `index.html` だけで動きます。外部の CSS・JavaScript・フォントは読み込みません。
- 見出しと配色は計画ライブラリ（shiga-hino-plans の `templates/hub.html`）と同じです。
- 他のダッシュボードへのリンクのうち、ヘッダーと共通のもの（トップ・計画・予算・人口）は `index.html` 末尾の `SITES` で URL を管理しています。

ダッシュボードを追加したときは、該当する分野の `<div class="cards">` にカードを1つ足し、この README の表にも1行足してください。

## OGP 画像の作り直し方

SNS で共有したときに出る画像は `og.png`（1200×630）です。編集元は `assets/og.svg` です。`tools/og_gen.py` は、ポータルと各ダッシュボードの計9本の OGP 画像の編集元を作るスクリプトで、各リポジトリの画像はここで作ったものを使っています。

1. `tools/og_gen.py` の `SITES` の文言や数字を直す。
2. `python3 tools/og_gen.py` を実行する。`tools/out/` にリポジトリ名ごとの svg が9本できる（`tools/out/` はリポジトリに含めない）。
3. `tools/out/` の svg を、Noto Sans CJK JP を入れた環境で 1200×630 の PNG に書き出す。
4. このリポジトリの分は `tools/out/hino-portal.svg` を `assets/og.svg` に、書き出した PNG を `og.png` に置き換える。他のリポジトリの分は、それぞれのリポジトリの og.svg と og.png を置き換える。

## ライセンス

コードは MIT License です（[LICENSE](LICENSE)）。
