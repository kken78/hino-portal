#!/usr/bin/env python3
"""共通の部品が hino-portal/shared の正本と同じかと、文字の大きさを確かめる（DESIGN.md 9.1）。

使い方：
  python3 shared/check.py [--fonts] [--shared <正本のフォルダ>] <HTML ファイル>...
  python3 shared/check.py --selftest
  正本のフォルダを省くと、このファイルと同じフォルダを使う。

確かめること（HTML ファイルごと）：
  1. <html lang="ja">
  2. <title> が「ページの題｜日野町データポータル（非公式）」の形（計画のページは「計画の名前｜計画ライブラリ｜日野町データポータル（非公式）」）
  3. <!-- portal-shared:css start --> … <!-- portal-shared:css end --> の中の <style> が shell.css と同じ
  4. <!-- portal-shared:header start --> … end の中が header.html と同じ。ただし分野のナビのちょうど1つに aria-current="page" を付けてよい
  5. <!-- portal-shared:siblings start --> … end の中が siblings-plan.html か siblings-stat.html と同じ。ただし、いま開いているページの <a href="…">題</a> を <span aria-current="page">題</span> に替えてよい
     （ポータルのトップと議会系のページには無くてよい）
  6. <!-- portal-shared:footer start --> … end の中の <footer> に、footer.html の固定の部分がある：
     dt の並びが「このページについて・出典・資料の時点・注意・データ・ソースコード・ライセンス」の順（無い項目は飛ばしてよい）、
     「このページについて」の最初の文が位置づけの文、「注意」の最初の文が固定の文
  7. 文字の大きさ（--fonts を付けたときだけ。DESIGN.md 5.2・9.1。決定 2026-11-08 段階3）。範囲は shiga-hino-plans の validate.mjs の文字の規則（7）（8）を写した：
     - <style> の font-size: の宣言、style 属性の font-size、font-size="…" 属性の値が、トークンの参照 var(--…) か、
       px・rem（1rem＝16px）・clamp()（最小値）・数だけ（SVG の属性。px とみなす）で 14px 以上。inherit は通す
     - var() で参照するトークンは、ページの中のすべての定義（@media の中の上書きを含む）が 14px 以上（トークンからトークンへの参照もたどる）
     - トークン --fs*・--portal-fs* の定義の値が 14px 以上
     - em・%・smaller などの親の大きさによる値、calc() などの判定できない値、font: の一括指定の大きさ、<small> の要素は誤り
     - Chart.js を読み込むページ（src に chart を含む <script> か new Chart( がある）では、Chart.defaults.font.size を 14 以上にしていること
       （Chart.js の既定は 12px）、JavaScript の font の size と ctx.font の px に 14 未満の数が無いこと
     ページの HTML の中だけを見る。外部の .js ファイルが実行時に作る文字は、実寸の検査（check_mobile.mjs）で見る
終了コード：問題が無ければ 0、あれば 1（問題をファイルごとに出す）。外部には何も読みに行かない。
--fonts：7 の文字の大きさの検査も行う。各リポジトリを段階3 で直すあいだは任意とし、9つのリポジトリが済んだら既定にする。
--selftest：文字の大きさの検査を、通る見本と通らない見本で確かめる（終了コード 0 なら見本どおり）。
"""
import os, re, sys, html

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "日野町データポータル（非公式）"
POSITION = "このページは、滋賀県日野町 政策参与の東健二郎が、個人として作成した試作です。日野町の公式のサイトではなく、町の見解を示すものでもありません。"
CAUTION = "内容の正確性を保証するものではありません。最新・正確な情報は日野町の公式ページでご確認ください。"
FOOT_ORDER = ["このページについて", "出典", "資料の時点", "注意", "データ", "ソースコード", "ライセンス"]

def norm(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*(<|>)\s*", r"\1", s)
    return s.strip()

def block(doc, name):
    m = re.search(rf"<!-- portal-shared:{name} start -->(.*?)<!-- portal-shared:{name} end -->", doc, re.S)
    return m.group(1) if m else None

def text_of(fragment):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", fragment))).strip()

def check(path, shared, fonts=False):
    problems = []
    doc = open(path, encoding="utf-8").read()
    # 1 lang
    if not re.search(r"<html[^>]*\blang=\"ja\"", doc):
        problems.append("<html lang=\"ja\"> が無い")
    # 2 title
    m = re.search(r"<title>(.*?)</title>", doc, re.S)
    title = norm(m.group(1)) if m else ""
    if not (title == SITE or title.endswith("｜" + SITE)):
        problems.append(f"<title> の形が違う：{title!r}")
    # 3 css
    css = block(doc, "css")
    if css is None:
        problems.append("portal-shared:css のブロックが無い")
    else:
        inner = re.search(r"<style>(.*?)</style>", css, re.S)
        want = open(os.path.join(shared, "shell.css"), encoding="utf-8").read()
        if not inner or norm(inner.group(1)) != norm(want):
            problems.append("portal-shared:css の中身が shell.css と違う")
    # 4 header
    hd = block(doc, "header")
    if hd is None:
        problems.append("portal-shared:header のブロックが無い")
    else:
        got = norm(hd)
        want = norm(open(os.path.join(shared, "header.html"), encoding="utf-8").read())
        got_plain, n = re.subn(r' aria-current="page"', "", got)
        if n > 1:
            problems.append("分野のナビの aria-current が2つ以上ある")
        if got_plain != want:
            problems.append("portal-shared:header の中身が header.html と違う")
    # 5 siblings
    sb = block(doc, "siblings")
    if sb is not None:
        got = norm(sb)
        ok = False
        for name in ("siblings-plan.html", "siblings-stat.html"):
            want = norm(open(os.path.join(shared, name), encoding="utf-8").read())
            # いま開いているページ：<a href="…">題</a> → <span aria-current="page">題</span>
            cands = [want] + [re.sub(re.escape(a), f'<span aria-current="page">{t}</span>', want, count=1)
                              for a, t in [(x.group(0), x.group(1)) for x in re.finditer(r'<a href="[^"]+">([^<]+)</a>', want)]]
            if got in cands:
                ok = True
        if not ok:
            problems.append("portal-shared:siblings の中身が siblings-plan.html・siblings-stat.html のどちらとも違う")
    # 6 footer
    ft = block(doc, "footer")
    if ft is None:
        problems.append("portal-shared:footer のブロックが無い")
    else:
        dts = [text_of(x) for x in re.findall(r"<dt>(.*?)</dt>", ft, re.S)]
        idx = [FOOT_ORDER.index(d) if d in FOOT_ORDER else -1 for d in dts]
        if -1 in idx:
            problems.append(f"フッターに決めていない項目がある：{[d for d, i in zip(dts, idx) if i < 0]}")
        if idx != sorted(idx):
            problems.append(f"フッターの項目の順が違う：{dts}")
        dds = re.findall(r"<dd>(.*?)</dd>", ft, re.S)
        pairs = dict(zip(dts, dds))
        if "このページについて" not in pairs or not text_of(pairs["このページについて"]).startswith(POSITION):
            problems.append("フッターの「このページについて」が位置づけの文で始まっていない")
        if "注意" not in pairs or not text_of(pairs["注意"]).startswith(CAUTION):
            problems.append("フッターの「注意」が固定の文で始まっていない")
    # 7 文字の大きさ（--fonts のときだけ）
    if fonts:
        problems.extend(font_problems(doc))
    return problems

# ---- 7. 文字の大きさ（DESIGN.md 5.2・9.1） ----
MIN_PX = 14.0
TOKEN_NAME = re.compile(r"^--(?:portal-)?fs(?:[\w-]*)$")

def strip_css_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)

def _first_arg(v):
    # clamp(a, b, c) の a。かっこの入れ子を考える
    depth, cur = 0, ""
    for ch in v:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            break
        cur += ch
    return cur.strip()

def size_of(v, tokens, seen=()):
    """値を px にする。戻り値は (最小の px または None, 理由)。トークンは全部の定義の最小を使う"""
    v = v.strip().rstrip(";").strip()
    v = re.sub(r"\s*!important$", "", v)
    if v == "inherit":
        return (None, "inherit")
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", v)
    if m:
        name = m.group(1)
        if name in seen:
            return (None, f"トークンの参照が循環している：{name}")
        defs = tokens.get(name)
        if not defs:
            return (None, f"参照しているトークン {name} の定義がページに無い")
        worst = None
        for d in defs:
            px, why = size_of(d, tokens, seen + (name,))
            if px is None and why != "inherit":
                return (None, f"{name}：{why}")
            if px is not None and (worst is None or px < worst):
                worst = px
        return (worst, f"{name}")
    m = re.fullmatch(r"clamp\((.*)\)", v, re.S)
    if m:
        return size_of(_first_arg(m.group(1)), tokens, seen)
    m = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)(px|rem)?", v)
    if m:
        n = float(m.group(1))
        return (n * 16 if m.group(2) == "rem" else n, "")
    if re.fullmatch(r"[\d.]+(em|%|ex|ch)", v) or v in ("smaller", "larger", "small", "x-small", "xx-small", "medium", "large"):
        return (None, "親や既定の大きさによる値（em・%・キーワード）は使えない")
    return (None, "判定できない値（px・rem・clamp・トークンの参照のみ可）")

def font_problems(doc):
    problems = []
    nocomment = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    styles = [strip_css_comments(x) for x in re.findall(r"<style[^>]*>(.*?)</style>", nocomment, re.S)]
    css = "\n".join(styles)
    # トークンの定義（:root や @media の中の上書きのすべて）
    tokens = {}
    for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;}]+)", css):
        tokens.setdefault(m.group(1), []).append(m.group(2).strip())
    for name, defs in tokens.items():
        if not TOKEN_NAME.match(name):
            continue
        for d in defs:
            px, why = size_of(d, tokens)
            if px is None and why != "inherit":
                problems.append(f"トークン {name}: {d} は{why}")
            elif px is not None and px < MIN_PX - 0.001:
                problems.append(f"トークン {name}: {d} が {px:g}px で 14px 未満")
    def judge(where, v):
        px, why = size_of(v, tokens)
        if px is None:
            if why != "inherit":
                problems.append(f"{where} font-size:{v.strip()} は{why}")
        elif px < MIN_PX - 0.001:
            problems.append(f"{where} font-size:{v.strip()} が {px:g}px で 14px 未満" + (f"（{why}）" if why else ""))
    for m in re.finditer(r"(?<![\w-])font-size\s*:\s*([^;}]+)", css):
        judge("<style> の", m.group(1))
    for m in re.finditer(r"(?:^|[{;\s])font\s*:\s*([^;}]+)", css):
        if re.search(r"\d(px|em|rem|pt|%)|\b(smaller|larger|x-small|xx-small)\b", m.group(1)):
            problems.append(f"<style> の font の一括指定に大きさがある：font:{m.group(1).strip()}")
    for m in re.finditer(r"\sstyle=\"([^\"]*)\"|\sstyle='([^']*)'", nocomment):
        st = m.group(1) if m.group(1) is not None else m.group(2)
        for f in re.finditer(r"(?<![\w-])font-size\s*:\s*([^;]+)", st):
            judge("style 属性の", f.group(1))
        for f in re.finditer(r"(?:^|;)\s*font\s*:\s*([^;]+)", st):
            if re.search(r"\d(px|em|rem|pt|%)", f.group(1)):
                problems.append(f"style 属性の font の一括指定に大きさがある：font:{f.group(1).strip()}")
    for m in re.finditer(r"\sfont-size=\"([^\"]*)\"|\sfont-size='([^']*)'", nocomment):
        v = m.group(1) if m.group(1) is not None else m.group(2)
        judge("font-size 属性の", v)
    n_small = len(re.findall(r"<small[\s>]", nocomment, re.I))
    if n_small:
        problems.append(f"<small> の要素が {n_small} か所ある（親より小さくなる。トークンで大きさを決める）")
    # Chart.js
    scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", nocomment, re.S | re.I)
    uses_chart = any(re.search(r"\bsrc=[\"'][^\"']*chart[^\"']*\.js", a, re.I) for a, _ in scripts) or \
        any("new Chart(" in b for _, b in scripts)
    js = "\n".join(b for _, b in scripts)
    if uses_chart:
        defaults = re.findall(r"Chart\.defaults\.font\.size\s*=\s*([^;\n]+)", js)
        if not defaults:
            problems.append("Chart.js を使うページで Chart.defaults.font.size を決めていない（Chart.js の既定は 12px）")
        for d in defaults:
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", d)]
            if not nums:
                problems.append(f"Chart.defaults.font.size = {d.strip()} は判定できない（数で書く）")
            elif min(nums) < MIN_PX:
                problems.append(f"Chart.defaults.font.size = {d.strip()} が 14 未満")
        for m in re.finditer(r"\bfont\s*:\s*\{([^{}]*)\}", js):
            for f in re.finditer(r"\bsize\s*:\s*([^,}\n]+)", m.group(1)):
                nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", f.group(1))]
                if not nums:
                    problems.append(f"Chart.js の font の size:{f.group(1).strip()} は判定できない（数で書く）")
                elif min(nums) < MIN_PX:
                    problems.append(f"Chart.js の font の size:{f.group(1).strip()} が 14 未満")
    for m in re.finditer(r"\.font\s*=\s*([\"'`])(.*?)\1", js):
        for f in re.finditer(r"(\d+(?:\.\d+)?)px", m.group(2)):
            if float(f.group(1)) < MIN_PX:
                problems.append(f"canvas の font = {m.group(2)!r} が 14px 未満")
    return problems

SELFTEST_OK = """<html lang="ja"><head><style>
:root{--portal-fs:16px;--portal-fs-sub:14px;--portal-fs-h3:20px;--fs-xs:var(--portal-fs-sub);--fs-h:clamp(1.25rem,3vw,1.5rem)}
@media (max-width:560px){:root{--fs-xs:.875rem}}
body{font:inherit;font-size:var(--portal-fs)} .a{font-size:var(--fs-xs)} .b{font-size:14px} .c{font-size:1rem} .d{font-size:var(--fs-h)} .e{font-size:inherit}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script></head><body>
<p style="font-size:16px">本文</p><svg><text font-size="14">14</text></svg>
<script>Chart.defaults.font.size = 14; new Chart(c,{options:{plugins:{legend:{labels:{font:{size:14}}}}}}); ctx.font = "700 14px sans-serif";</script>
</body></html>"""

SELFTEST_NG = [
    ("12px の直接の指定", "<style>.a{font-size:12px}</style>"),
    ("<small>", "<p>本文<small>注</small></p>"),
    ("em の指定", "<style>.a{font-size:.8em}</style>"),
    ("% の指定", "<style>.a{font-size:90%}</style>"),
    ("clamp の最小値が 12px", "<style>.a{font-size:clamp(12px,2vw,16px)}</style>"),
    ("clamp の最小値が .75rem のトークン", "<style>:root{--fs-3xs:clamp(.75rem,1vw,1rem)}.a{font-size:var(--fs-3xs)}</style>"),
    ("Chart.js の size:12", "<script src=\"chart.umd.min.js\"></script><script>Chart.defaults.font.size = 14; new Chart(c,{options:{scales:{x:{ticks:{font:{size:12}}}}}});</script>"),
    ("Chart.js の既定の大きさを決めていない", "<script>new Chart(c,{});</script>"),
    ("Chart.defaults.font.size = 12", "<script>Chart.defaults.font.size = 12; new Chart(c,{});</script>"),
    ("canvas の 12px", "<script>ctx.font = '12px sans-serif';</script>"),
    ("13px のトークン", "<style>:root{--fs-small:13px}</style>"),
    ("狭い画面での 13px の上書き", "<style>:root{--fs-tab:14px}@media (max-width:560px){:root{--fs-tab:13px}}.t{font-size:var(--fs-tab)}</style>"),
    ("トークンからトークンへの参照の先が 12px", "<style>:root{--fs-a:12px;--fs-b:var(--fs-a)}.a{font-size:var(--fs-b)}</style>"),
    ("定義の無いトークンの参照", "<style>.a{font-size:var(--fs-none)}</style>"),
    ("font の一括指定の大きさ", "<style>.a{font:700 13px/1.4 sans-serif}</style>"),
    ("style 属性の 12px", "<p style=\"color:red;font-size:12px\">x</p>"),
    ("SVG の font-size 属性 12", "<svg><text font-size=\"12\">x</text></svg>"),
    ("calc の指定", "<style>.a{font-size:calc(1rem - 2px)}</style>"),
    ("smaller の指定", "<style>.a{font-size:smaller}</style>"),
]

def selftest():
    bad = 0
    ok = font_problems(SELFTEST_OK)
    if ok:
        bad += 1
        print("通る見本で問題が出た：")
        for p in ok:
            print(f"  - {p}")
    else:
        print("通る見本：問題なし（正しい）")
    for name, frag in SELFTEST_NG:
        ps = font_problems(f"<html lang=\"ja\"><head></head><body>{frag}</body></html>")
        if ps:
            print(f"通らない見本「{name}」：問題 {len(ps)} 件（正しい）　{ps[0]}")
        else:
            bad += 1
            print(f"通らない見本「{name}」：問題が出なかった（誤り）")
    print(f"見本 {1 + len(SELFTEST_NG)} 件のうち、見本どおりでないもの {bad} 件")
    return 1 if bad else 0

def main(argv):
    shared = HERE
    fonts = False
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == "--selftest":
            return selftest()
        if argv[i] == "--fonts":
            fonts = True; i += 1; continue
        if argv[i] == "--shared":
            shared = argv[i + 1]; i += 2
        else:
            files.append(argv[i]); i += 1
    if not files:
        print(__doc__); return 2
    bad = 0
    for f in files:
        ps = check(f, shared, fonts)
        if ps:
            bad += 1
            print(f"{f}：問題 {len(ps)} 件")
            for p in ps:
                print(f"  - {p}")
        else:
            print(f"{f}：共通の部品は正本と同じ" + ("。文字の大きさは 14px 以上" if fonts else ""))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
