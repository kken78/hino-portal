# 共通の部品（正本）

ポータルの下のページ（計画と予算、統計とくらし）が共通に使う、見出し・分野のナビ・ページの一覧・フッターの正本。DESIGN.md 2章（構造）と 9.1（検査）による。議会系のページ（council-dashboard、hino-council-search）は使わない（8章）。

| ファイル | 中身 | ページでの置き方 |
|---|---|---|
| shell.css | 共通の部品の CSS。クラス名は `portal-` で始まり、ページの CSS とぶつからない | `<head>` の中に `<!-- portal-shared:css start --><style>…</style><!-- portal-shared:css end -->` として写す |
| header.html | 共通の見出し（名前・「非公式」の印・分野のナビ） | `<body>` の最初に `<!-- portal-shared:header start -->…<!-- portal-shared:header end -->` として写す。いまの分野のリンクに `aria-current="page"` を付ける（1つだけ） |
| siblings-plan.html・siblings-stat.html | 分野の中のページの一覧（2.3） | ページの見出しの中（`.portal-page` の最後）に `<!-- portal-shared:siblings start -->…end -->` として写す。いま開いているページは `<a href="…">題</a>` を `<span aria-current="page">題</span>` に替える |
| footer.html | フッターの型（2.5 の7項目） | `<!-- portal-shared:footer start -->…end -->` として置き、`{{…}}` をページの中身に替える。項目の順は変えない。当てはまらない項目（ポータルのトップの「出典」など）は飛ばしてよい。「このページについて」の最初の文と「注意」の文は変えない |
| check.py | 上が正本と同じかを確かめる道具 | 各リポジトリの CI で、hino-portal を浅く取ってきて `python3 hino-portal/shared/check.py <HTML>` を走らせる（下） |

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

## CI での確かめ方

```yaml
- name: 共通の部品が hino-portal の正本と同じか
  run: |
    git clone --depth 1 https://github.com/kken78/hino-portal.git /tmp/hino-portal
    python3 /tmp/hino-portal/shared/check.py index.html
```

## 正本を変えるとき

1. DESIGN.md を先に改め、決定の記録に書く。
2. この正本を変え、hino-portal の index.html を合わせて PR にする。
3. 各リポジトリで写し直す（各リポジトリの CI が、正本との違いを知らせる）。
