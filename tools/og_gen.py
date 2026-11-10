"""日野町データポータルの各ダッシュボードの OGP 画像（1200×630、og.png）を作る。

型：左に題と要点、右に白い枠の小さな図、下に位置づけの一文（hino-plan-dashboard の旧 assets/ogp.svg の構成）。
決まり：
- 文字はすべて 24px 以上（SNS の縮小表示でも読める大きさ）
- 色は意味を伝えるときだけ使う。棒は1色。良し悪しの色分けをしない
- 数字はリポジトリのデータから取ったものだけを書く。キャッチコピー・絵文字・評価の語を入れない
配色：計画と予算はポータルの藍、統計・くらしは各ページの色、議会は各ページの色（独立）。
"""
import html, pathlib, sys

OUT = pathlib.Path(__file__).parent / "out"
F = "Noto Sans CJK JP, Noto Sans JP, sans-serif"
E = html.escape
MIN = 24

FOOT_PORTAL = "公開資料から作成した個人の試作（非公式）｜日野町データポータル"
FOOT_COUNCIL = "一個人による提案・試作です。議会の公式な成果物ではありません"


def pal(c1, c2, light, accent, track, ink="#1A2333", muted="#5B6B85", footer=FOOT_PORTAL):
    return dict(c1=c1, c2=c2, light=light, accent=accent, track=track, ink=ink, muted=muted, footer=footer)


AI = pal("#1E4E9C", "#123563", "#C9D7EE", "#1E4E9C", "#E9EEF7")                       # 計画と予算・ポータル
STAT = pal("#1D4F8A", "#14325C", "#C6D6EC", "#1D4F8A", "#E8EEF6")                     # 日野のすがた
CHOI = pal("#1F8A70", "#0C5E4B", "#C4EADF", "#167359", "#E4F2ED", ink="#16302A", muted="#4E6A62")  # チョイソコひの
POP = AI                                                                                 # 地区別人口
PLUM = pal("#7A1F5C", "#5E1646", "#EBCFE0", "#7A1F5C", "#F2ECE3", ink="#231B26", muted="#6E6377", footer=FOOT_COUNCIL)
HINONA = pal("#8E2A4D", "#1B2A41", "#F4DDE4", "#8E2A4D", "#F5F3EE", ink="#1B2A41", muted="#52606D", footer=FOOT_COUNCIL)


def t(x, y, s, size, fill, weight=700, extra=""):
    assert size >= MIN, (s, size)
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" {extra}>{E(s)}</text>'


def w_of(s, size):
    """およその文字幅（全角1.0、半角0.58）。"""
    return sum(size if ord(c) > 0x2000 else size * 0.58 for c in s)


CX, CW = 760, 400          # 右の枠の x と幅
IX, IR = CX + 28, CX + CW - 28   # 枠の内側の左右


def page(p, titles, sub, metrics, caption, card, eyebrow="滋賀県 日野町"):
    body, ch = card(p)
    cy = max(110, 330 - ch // 2)
    s = [f'<svg width="1200" height="630" viewBox="0 0 1200 630" xmlns="http://www.w3.org/2000/svg">',
         '<defs>',
         f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["c1"]}"/><stop offset="1" stop-color="{p["c2"]}"/></linearGradient>',
         '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="14" flood-color="#000" flood-opacity="0.18"/></filter>',
         '</defs>',
         '<rect width="1200" height="630" fill="url(#bg)"/>',
         '<path d="M1200,0 L1200,260 C1040,300 980,150 820,200 C700,236 640,120 540,150 L540,0 Z" fill="#ffffff" opacity="0.05"/>',
         '<path d="M0,630 L0,470 C160,430 240,560 420,520 C560,490 660,600 820,560 L1200,560 L1200,630 Z" fill="#ffffff" opacity="0.06"/>',
         f'<g font-family="{F}">',
         t(80, 104, eyebrow, 24, p["light"], extra='letter-spacing="4"'),
         f'<rect x="80" y="122" width="64" height="4" rx="2" fill="{p["light"]}" opacity="0.8"/>']
    for line, y, size in zip(titles, [206, 284], [72, 60]):
        assert w_of(line, size) < CX - 100, line
        s.append(t(78, y, line, size, "#ffffff", extra='letter-spacing="1"'))
    sy = 352 if len(titles) == 2 else 290
    lines = sub if isinstance(sub, list) else [sub]
    for i, l in enumerate(lines):
        assert w_of(l, 25) < CX - 100, l
        s.append(t(82, sy + i * 36, l, 25, "#ffffff", 500, 'opacity="0.88"'))
    x = 82
    for num, unit in metrics:
        s.append(t(x, 486, num, 58, "#ffffff"))
        x += w_of(num, 58) + 6
        if unit:
            s.append(t(round(x), 486, unit, 26, p["light"]))
            x += w_of(unit, 26)
        x += 44
    assert x < CX + 20, metrics
    s.append(t(82, 532, caption, 24, p["light"], 500))
    s.append(t(80, 592, p["footer"], 24, p["light"], 500, 'opacity="0.85"'))
    s.append('</g>')
    s.append(f'<g filter="url(#soft)"><rect x="{CX}" y="{cy}" width="{CW}" height="{ch}" rx="20" fill="#ffffff"/></g>')
    s.append(f'<g font-family="{F}" transform="translate(0,{cy})">{body}</g>')
    s.append('</svg>')
    return "\n".join(s)


def head(p, title, sub):
    for l, sz in [(title, 24)] + [(x, 24) for x in (sub if isinstance(sub, list) else [sub])]:
        assert w_of(l, sz) <= IR - IX, l
    out = [t(IX, 50, title, 24, p["ink"])]
    y = 50
    for l in (sub if isinstance(sub, list) else [sub]):
        y += 32
        out.append(t(IX, y, l, 24, p["muted"], 500))
    return "".join(out), y


def bars(title, sub, rows, fmt=str, label_w=None):
    """rows: (ラベル, 値)。ラベルが短いときは棒の左、長いときは棒の上に置く。棒は1色。"""
    def card(p):
        h, y = head(p, title, sub)
        out = [h]
        top = max(v for _, v in rows)
        lw = label_w if label_w is not None else max(w_of(l, 24) for l, _ in rows)
        vw = max(w_of(fmt(v), 24) for _, v in rows)
        inline = lw + vw + 120 <= IR - IX
        y += 24
        for lab, v in rows:
            if inline:
                y += 40
                out.append(t(IX, y, lab, 24, p["ink"]))
                bx, bw = IX + lw + 14, IR - IX - lw - vw - 28
                out.append(f'<rect x="{bx}" y="{y-16}" width="{bw:.0f}" height="14" rx="7" fill="{p["track"]}"/>')
                out.append(f'<rect x="{bx}" y="{y-16}" width="{bw*v/top:.0f}" height="14" rx="7" fill="{p["accent"]}"/>')
                out.append(t(IR, y, fmt(v), 24, p["ink"], 700, 'text-anchor="end"'))
            else:
                y += 34
                out.append(t(IX, y, lab, 24, p["ink"]))
                out.append(t(IR, y, fmt(v), 24, p["ink"], 700, 'text-anchor="end"'))
                y += 10
                out.append(f'<rect x="{IX}" y="{y}" width="{IR-IX}" height="12" rx="6" fill="{p["track"]}"/>')
                out.append(f'<rect x="{IX}" y="{y}" width="{(IR-IX)*v/top:.0f}" height="12" rx="6" fill="{p["accent"]}"/>')
                y += 14
        return "".join(out), y + 30
    return card


def items(title, sub, rows):
    """rows: (左の語, 右の語)。右の語は灰色。"""
    def card(p):
        h, y = head(p, title, sub)
        out = [h]
        y += 20
        for a, b in rows:
            assert w_of(a, 24) + w_of(b, 24) + 16 <= IR - IX, (a, b)
            y += 44
            out.append(f'<line x1="{IX}" y1="{y-34}" x2="{IR}" y2="{y-34}" stroke="{p["track"]}" stroke-width="2"/>')
            out.append(t(IX, y, a, 24, p["ink"]))
            out.append(t(IR, y, b, 24, p["muted"], 500, 'text-anchor="end"'))
        return "".join(out), y + 34
    return card


def chips(title, sub, names, notes):
    def card(p):
        h, y = head(p, title, sub)
        out = [h]
        y += 22
        x = IX
        for n in names:
            w = w_of(n, 24) + 28
            if x + w > IR:
                x = IX; y += 46
            out.append(f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="38" rx="19" fill="{p["track"]}"/>')
            out.append(t(round(x + 14), y + 27, n, 24, p["ink"]))
            x += w + 10
        y += 46
        for n in notes:
            assert w_of(n, 24) <= IR - IX, n
            y += 34
            out.append(t(IX, y, n, 24, p["muted"], 500))
        return "".join(out), y + 30
    return card


def search(title, sub, query, rows):
    def card(p):
        h, y = head(p, title, sub)
        out = [h]
        y += 22
        out.append(f'<rect x="{IX}" y="{y}" width="{IR-IX}" height="50" rx="10" fill="{p["track"]}" stroke="#DDD7CA"/>')
        out.append(t(IX + 16, y + 34, query, 24, p["ink"]))
        out.append(f'<rect x="{IR-76}" y="{y+8}" width="68" height="34" rx="8" fill="{p["accent"]}"/>')
        out.append(t(IR - 42, y + 34, "検索", 24, "#ffffff", 700, 'text-anchor="middle"'))
        y += 50
        for a, b in rows:
            assert w_of(a, 24) + w_of(b, 24) + 16 <= IR - IX, (a, b)
            y += 44
            out.append(t(IX, y, a, 24, p["ink"]))
            out.append(t(IR, y, b, 24, p["muted"], 500, 'text-anchor="end"'))
        return "".join(out), y + 30
    return card


def oku(v):
    return f"{v:.1f}"


def comma(v):
    return f"{v:,}"


SITES = {
    # 計画と予算
    "hino-portal": page(AI, ["日野町", "データポータル"], "町の公開資料を、元のページまでたどれる形に",
                        [("9", "ダッシュボード"), ("3", "分野")], "計画と予算　/　議会　/　統計・くらし",
                        items("9つのダッシュボード", "町が公開している資料から作成",
                              [("計画と予算", "4"), ("議会", "2"), ("統計・くらし", "3")])),
    "shiga-hino-plans": page(AI, ["計画", "ライブラリ"], "町の計画を、原典のページつきで読む",
                             [("43", "計画"), ("15,409", "件を照合")], "記載を原典PDFのページと照らして掲載",
                             items("原典との照合", ["記載ごとに、原典PDFの", "ページと照らす"],
                                   [("基本理念", "原典のページ"), ("施策の方向", "原典のページ"),
                                    ("成果指標", "原典のページ"), ("事業", "原典のページ")])),
    "hino-plan-dashboard": page(AI, ["総合計画", "指標と事業費"], "第6次日野町総合計画（令和3〜12年度）",
                                [("34", "分野"), ("79", "指標")], "成果指標　/　実施計画　/　住民意識調査",
                                items("収録している資料", "資料ごとの時点",
                                      [("成果指標", "R7中間・R12最終"), ("実施計画", "令和7〜9年度"),
                                       ("住民意識調査", "令和6年度")])),
    "hino-zaisei": page(AI, ["予算と決算", "町の財政"], "当初予算の主な事業と、補正予算・決算・財政指標",
                        [("1,031", "事業"), ("令和3〜8", "年度")], "附表に載った事業の集計で、町の予算の全体ではない",
                        bars("主な事業の予算額の計（億円）", ["令和3〜8年度", "当初予算の概要 附表"],
                             [("令和3年度", 56.1), ("令和4年度", 61.2), ("令和5年度", 60.4),
                              ("令和6年度", 63.6), ("令和7年度", 69.9), ("令和8年度", 79.5)], oku)),
    # 統計・くらし
    "hino-population": page(POP, ["地区別人口", "月ごとの推移"], "町が毎月公表する人口情報を、地区ごとに",
                            [("7", "地区"), ("毎月", "")], "世帯数　/　男　/　女　/　計（住民基本台帳）",
                            chips("7つの地区", "地区合計を月ごとに並べる",
                                  ["日野", "東桜谷", "西桜谷", "鎌掛", "南比都佐", "必佐", "西大路"],
                                  ["検算：男＋女＝計", "7地区の合計＝町全体"])),
    "hino-dashboard": page(STAT, ["日野のすがた", "統計ダッシュボード"], "人口・産業・財政まで、町の統計をグラフで",
                           [("27", "項目"), ("11", "分野")], "統計でわかる！日野のすがた　ほか",
                           bars("年間出生数（人）", "人口動態", [("令和2年", 142), ("令和3年", 122), ("令和4年", 117),
                                                         ("令和5年", 106), ("令和6年", 105)])),
    "choisoko-hino-dashboard": page(CHOI, ["チョイソコひの", "利用状況"], "デマンド型乗合交通の運行レポートを時点ごとに",
                                    [("30,855", "件"), ("2,771", "人")], "累計の利用件数　/　登録会員数（令和8年9月末）",
                                    bars("累計の利用件数（件）", "運行開始（令和5年3月）から",
                                         [("R5.3", 304), ("R6.3", 5634), ("R7.3", 11615), ("R8.3", 22489),
                                          ("R8.9", 30855)], comma)),
    # 議会
    "council-dashboard": page(PLUM, ["議会だより", "一般質問"], "議会だよりの一般質問を、テーマから引く",
                              [("326", "問"), ("13", "号")], "議会だより 第24〜36号",
                              bars("テーマ別の一般質問（問）", "議会だより 第24〜36号",
                                   [("子育て・教育", 82), ("行財政・行政運営", 38), ("農林業", 33), ("交通・公共交通", 28)]),
                              eyebrow="滋賀県 日野町議会"),
    "hino-council-search": page(HINONA, ["会議録", "横断検索"], "会議録を、発言単位で全文検索",
                                [("66", "会議"), ("31,263", "発言")], "2017〜2026年の会議録",
                                search("表記のちがいを吸収", "発言単位で全文検索", "通学路　安全",
                                       [("異体字", "髙＝高"), ("地名のよみ", "かいがけ→鎌掛"), ("元号と西暦", "令和7⇄2025")]),
                                eyebrow="滋賀県 日野町議会"),
}

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, svg in SITES.items():
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(len(SITES), "svg")
