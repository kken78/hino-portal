# 日野町データポータル（非公式）

https://kken78.github.io/hino-portal/

滋賀県日野町のホームページで公開されている計画・議会の記録・統計をもとにしたダッシュボードの入口ページです。各ダッシュボードはそれぞれ別のリポジトリで公開しています。

| 分野 | ダッシュボード | リポジトリ |
|---|---|---|
| 計画と予算 | 計画ライブラリ | [shiga-hino-plans](https://github.com/kken78/shiga-hino-plans) |
| 計画と予算 | 第6次総合計画 指標と事業費 | [hino-plan-dashboard](https://github.com/kken78/hino-plan-dashboard) |
| 計画と予算 | 令和8年度 主な事業 | [hino-budget](https://github.com/kken78/hino-budget) |
| 議会 | 議会だより・一般質問 | [council-dashboard](https://github.com/kken78/council-dashboard) |
| 議会 | 会議録 横断検索 | [hino-council-search](https://github.com/kken78/hino-council-search) |
| 統計・くらし | 地区別人口 | [hino-population](https://github.com/kken78/hino-population) |
| 統計・くらし | 日野のすがた | [hino-dashboard](https://github.com/kken78/hino-dashboard) |
| 統計・くらし | チョイソコひの 利用状況 | [choisoko-hino-dashboard](https://github.com/kken78/choisoko-hino-dashboard) |

## 構成

- `index.html` だけで動きます。外部の CSS・JavaScript・フォントは読み込みません。
- 見出しと配色は計画ライブラリ（shiga-hino-plans の `templates/hub.html`）と同じです。
- 他のダッシュボードへのリンクのうち、ヘッダーと共通のもの（トップ・計画・予算・人口）は `index.html` 末尾の `SITES` で URL を管理しています。

ダッシュボードを追加したときは、該当する分野の `<div class="cards">` にカードを1つ足し、この README の表にも1行足してください。

## ライセンス

コードは MIT License です（[LICENSE](LICENSE)）。
