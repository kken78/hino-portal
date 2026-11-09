#!/usr/bin/env python3
"""共通の部品が hino-portal/shared の正本と同じかと、文字の大きさ・表記・太さ・外部からの読み込みを確かめる（DESIGN.md 9.1）。

使い方：
  python3 shared/check.py [--no-shared] [--hyoki] [--strict-external] [--shared <正本のフォルダ>] <HTML ファイル>...
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
  7. 文字の大きさ（DESIGN.md 5.2・9.1。決定 2026-11-08 段階3）。範囲は shiga-hino-plans の validate.mjs の文字の規則（7）（8）を写した：
     - <style> の font-size: の宣言、style 属性の font-size、font-size="…" 属性の値が、トークンの参照 var(--…) か、
       px・rem（1rem＝16px）・clamp()（最小値）・数だけ（SVG の属性。px とみなす）で 14px 以上。inherit は通す
     - var() で参照するトークンは、ページの中のすべての定義（@media の中の上書きを含む）が 14px 以上（トークンからトークンへの参照もたどる）
     - トークン --fs*・--portal-fs* の定義の値が 14px 以上
     - em・%・smaller などの親の大きさによる値、calc() などの判定できない値、font: の一括指定の大きさ、<small> の要素は誤り
     - Chart.js を読み込むページ（src に chart を含む <script> か new Chart( がある）では、Chart.defaults.font.size を 14 以上にしていること
       （Chart.js の既定は 12px）、JavaScript の font の size と ctx.font の px に 14 未満の数が無いこと
     ページの HTML の中だけを見る。外部の .js ファイルが実行時に作る文字は、実寸の検査（check_mobile.mjs）で見る
  8. 表記（DESIGN.md 3.3・5.6・6.4。--hyoki のときだけ）。本文の文字（<script>・<style> の中とコメントを除き、alt・aria-label・title 属性の字を含める）で：
     - ▲・▼・↑・↓ の直後（空白をはさんでもよい）に数字か「増」「減」が無い
     - 半角の「+」の直後に数字が無い（全角の「＋」は式の足し算に使うので見ない）。URL と <code>・<pre> の中は見ない
     - 上の2つと次の語の検査は、<q>（原典の字の引用）の中を見ない
     - 「くわしく」「こちら」「前年比」「前年度比」「前回比」が無い
     - target="_blank" の <a> に「新しいタブで開きます」の字（要素の中の文字、a の aria-label・title、中の要素の alt・aria-label・title）がある
     - 「R」＋数字＋（年・.・〜）の形があるページに「R＝令和」か「R は令和」の字がある
  9. 太さ（DESIGN.md 5.2。--hyoki のときだけ）。<style> と style 属性の font-weight と、font の一括指定の太さが
     400・700・normal・bold・inherit・800 のどれか（800 は数字の札の主の値に限るが、判定できないので通す）。トークンの参照はたどる
  10. 外部からの読み込み（DESIGN.md 4.2）。<script src>・<link href>（rel が canonical・alternate のものを除く）・@import・url(…)・<img src> の
     http(s):// か // で始まる URL。既定は警告（終了コードを変えない）。--strict-external で誤りにする
     警告は「  警告：」で始まる行に出す（各リポジトリの CI が「  - 」で始まる行を問題として数えているため）
終了コード：問題が無ければ 0、あれば 1（問題をファイルごとに出す）。外部には何も読みに行かない。
1〜7 をすべて行うのが既定。7 の文字の大きさの検査は、段階3 が9つのリポジトリで済んだので既定にした（2026-11-08）。
--fonts：互換のために残した指定。付けても付けなくても同じ（7 を行う）。
--no-shared：共通の部品を持たないページ（議会系の council-dashboard・hino-council-search）のための指定。
  2 の <title> の形と、3〜6 の共通の部品（css・header・siblings・footer のブロック）の検査を外す。1 の lang と 7 の文字の大きさは行う。
--hyoki：8 の表記と 9 の太さの検査を行う。各リポジトリの段階4 の PR が出そろうまでは、付けたときだけ行う（出そろったら既定にする。DESIGN.md 9.1）。
--strict-external：10 の外部からの読み込みを、警告でなく誤りにする（段階5 で CDN を同梱に替えたあとに CI に付ける）。
--selftest：文字の大きさ・表記・太さ・外部からの読み込みの検査を通る見本と通らない見本で、既定で文字の検査が動くこと、
  --no-shared で <title> と共通の部品の検査が外れること、--hyoki と --strict-external の働きを見本で確かめる（終了コード 0 なら見本どおり）。
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

def check(path, shared, fonts=True, shared_parts=True, hyoki=False, strict_external=False):
    doc = open(path, encoding="utf-8").read()
    return check_doc(doc, shared, fonts, shared_parts, hyoki, strict_external)

def check_doc(doc, shared, fonts=True, shared_parts=True, hyoki=False, strict_external=False):
    """戻り値は (誤り, 警告)。警告は終了コードを変えない"""
    problems, warnings = [], []
    # 1 lang
    if not re.search(r"<html[^>]*\blang=\"ja\"", doc):
        problems.append("<html lang=\"ja\"> が無い")
    if shared_parts:
        problems.extend(shared_problems(doc, shared))
    # 7 文字の大きさ（既定で行う）
    if fonts:
        problems.extend(font_problems(doc))
    # 8・9 表記と太さ（--hyoki のときだけ。各リポジトリの段階4 の PR が出そろったら既定にする）
    if hyoki:
        problems.extend(hyoki_problems(doc))
        problems.extend(weight_problems(doc))
    # 10 外部からの読み込み（既定は警告。--strict-external で誤り）
    ext = external_findings(doc)
    if ext:
        msg = f"外部からの読み込みがある（{len(ext)} 件。4.2）：" + "、".join(ext)
        (problems if strict_external else warnings).append(msg)
    return problems, warnings

def shared_problems(doc, shared):
    """2〜6：<title> の形と、共通の部品の写し（--no-shared のときは行わない）"""
    problems = []
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

# ---- 8・9. 表記と太さ（DESIGN.md 3.3・5.2・5.6・6.4。--hyoki を付けたときだけ） ----
# ---- 10. 外部からの読み込み（DESIGN.md 4.2。既定は警告。--strict-external で誤り） ----

def _skeleton(doc):
    """コメントを除き、<script>・<style> の中身を空にした HTML（要素の開始タグと属性は残す）"""
    d = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    d = re.sub(r"(<script\b[^>]*>).*?(</script\s*>)", r"\1\2", d, flags=re.S | re.I)
    d = re.sub(r"(<style\b[^>]*>).*?(</style\s*>)", r"\1\2", d, flags=re.S | re.I)
    return d

ATTR_TEXT = re.compile(r"""\s(alt|aria-label|title)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)

def _attr_texts(tag_html):
    return [html.unescape(m.group(2) if m.group(2) is not None else m.group(3)) for m in ATTR_TEXT.finditer(tag_html)]

def body_text(doc, drop_code=False):
    """本文の文字。<script>・<style> の中と HTML のコメントを除き、alt・aria-label・title 属性の字を含める。
    属性の字は、要素の文字とつながらないように改行で区切って末尾に足す。drop_code なら <code>・<pre> の中を除く"""
    d = _skeleton(doc)
    d = re.sub(r"<(script|style)\b[^>]*>\s*</\1\s*>", "", d, flags=re.I)
    if drop_code:
        d = re.sub(r"<(code|pre)\b[^>]*>.*?</\1\s*>", "", d, flags=re.S | re.I)
    attrs = []
    for t in re.finditer(r"<[a-zA-Z][^>]*>", d):
        attrs.extend(_attr_texts(t.group(0)))
    # 区切りの要素（段落・表のセル・項目など）の境目は改行にし、隣の要素の字とつなげない。<span> などの中の字はつなげる
    d = re.sub(r"</?(?:p|div|td|th|tr|li|dt|dd|h[1-6]|br|hr|section|article|table|thead|tbody|ul|ol|dl|nav|header|footer|main|option|caption|figcaption|summary|details|button|label|title)\b[^>]*>", "\n", d, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", d))
    return text + "\n" + "\n".join(attrs)

def _examples(text, pattern, n=3, width=8):
    ms = list(re.finditer(pattern, text))
    ex = []
    for m in ms[:n]:
        s = text[max(0, m.start() - width):m.end() + width]
        ex.append("「" + re.sub(r"\s+", " ", s).strip() + "」")
    return len(ms), "、".join(ex)

SIGN_MARK = r"[▲▼↑↓]\s*(?:[0-9０-９]|増|減)"
PLUS_NUM = r"\+[0-9０-９]"
URL = r"(?:https?:)?//[^\s\"'<>）」]+"
WORDS = ["くわしく", "こちら", "前年比", "前年度比", "前回比"]
R_YEAR = r"(?<![A-Za-zＡ-Ｚａ-ｚ])R[0-9０-９]+(?:年|\.|〜|～)"
R_NOTE = r"R\s*[＝=]\s*令和|R\s*は令和"
NEW_TAB = "新しいタブで開きます"

def hyoki_problems(doc):
    """8 表記（DESIGN.md 3.3・5.6・6.4）"""
    problems = []
    doc = re.sub(r"<q\b[^>]*>.*?</q\s*>", " ", doc, flags=re.S | re.I)   # 原典の字の引用の中は見ない（6.4）
    text = body_text(doc)
    n, ex = _examples(text, SIGN_MARK)
    if n:
        problems.append(f"表記：増減の印（▲・▼・↑・↓）の直後に数字か増・減がある（{n} か所。例 {ex}）。負の値は △、正の値は印なし、向きは文言（3.3）")
    plain = re.sub(URL, " ", body_text(doc, drop_code=True))
    n, ex = _examples(plain, PLUS_NUM)
    if n:
        problems.append(f"表記：「+」の直後に数字がある（{n} か所。例 {ex}）。正の値に + を付けない（6.4）")
    for w in WORDS:
        n, ex = _examples(text, re.escape(w))
        if n:
            problems.append(f"表記：「{w}」がある（{n} か所。例 {ex}）（5.6・6.2）")
    sk = _skeleton(doc)
    bad = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a\s*>", sk, re.S | re.I):
        attrs, inner = m.group(1), m.group(2)
        if not re.search(r"""\btarget\s*=\s*(?:"_blank"|'_blank'|_blank\b)""", attrs, re.I):
            continue
        words = [html.unescape(re.sub(r"<[^>]+>", "", inner))]
        words += [v for k, v in [(x.group(1).lower(), html.unescape(x.group(2) if x.group(2) is not None else x.group(3)))
                                 for x in ATTR_TEXT.finditer(" " + attrs)] if k in ("aria-label", "title")]
        for t in re.finditer(r"<[a-zA-Z][^>]*>", inner):
            words.extend(_attr_texts(t.group(0)))
        if not any(NEW_TAB in w for w in words):
            bad.append(re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", inner))).strip()[:20])
    if bad:
        problems.append(f"表記：target=\"_blank\" のリンクに「{NEW_TAB}」の字が無い（{len(bad)} か所。例 {'、'.join('「' + b + '」' for b in bad[:3])}）（5.6）")
    n, ex = _examples(text, R_YEAR)
    if n and not re.search(R_NOTE, text):
        problems.append(f"表記：R＋数字の年度の略記がある（{n} か所。例 {ex}）のに「R＝令和」の注が無い（6.4）")
    return problems

WEIGHT_OK = {"400", "700", "800", "normal", "bold", "inherit"}
WEIGHT_WORDS = {"bold", "bolder", "lighter", "normal"}

def _weight_of(v, defs, seen=()):
    """太さの値を、許す値の集合で判定する。戻り値は 誤りの理由 か None"""
    v = re.sub(r"\s*!important$", "", v.strip().rstrip(";").strip())
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", v)
    if m:
        name = m.group(1)
        if name in seen or name not in defs:
            return f"参照しているトークン {name} の定義がページに無いか循環している"
        for d in defs[name]:
            why = _weight_of(d, defs, seen + (name,))
            if why:
                return f"{name}：{why}"
        return None
    if v in WEIGHT_OK:
        return None
    return f"{v} は使えない（400・700・normal・bold・inherit と、数字の札の主の値の 800 だけ）"

def weight_problems(doc):
    """9 太さ（DESIGN.md 5.2）。<style> と style 属性の font-weight と、font の一括指定の太さ"""
    problems = []
    nocomment = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    css = "\n".join(strip_css_comments(x) for x in re.findall(r"<style[^>]*>(.*?)</style>", nocomment, re.S))
    defs = {}
    for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;}]+)", css):
        defs.setdefault(m.group(1), []).append(m.group(2).strip())
    found = {}
    def judge(where, v):
        why = _weight_of(v, defs)
        if why:
            key = f"{where}：{why}"
            found[key] = found.get(key, 0) + 1
    def shorthand(where, v):
        for t in v.split():
            if t.startswith("var(") or t == "inherit":
                break
            if re.fullmatch(r"[1-9]00", t) or t in ("bolder", "lighter"):
                judge(where + " font の一括指定の太さ", t)
            if re.match(r"[\d.]+(px|rem|em|pt|%)", t):
                break
    for m in re.finditer(r"(?<![\w-])font-weight\s*:\s*([^;}]+)", css):
        judge("<style> の font-weight", m.group(1))
    for m in re.finditer(r"(?:^|[{;\s])font\s*:\s*([^;}]+)", css):
        shorthand("<style> の", m.group(1))
    sk = _skeleton(doc)
    for m in re.finditer(r"\sstyle=\"([^\"]*)\"|\sstyle='([^']*)'", sk):
        st = m.group(1) if m.group(1) is not None else m.group(2)
        for f in re.finditer(r"(?<![\w-])font-weight\s*:\s*([^;]+)", st):
            judge("style 属性の font-weight", f.group(1))
        for f in re.finditer(r"(?:^|;)\s*font\s*:\s*([^;]+)", st):
            shorthand("style 属性の", f.group(1))
    for k, n in found.items():
        problems.append(f"太さ：{k}（{n} か所）（5.2）")
    return problems

EXT = r"(?:https?:)?//"

def external_findings(doc):
    """10 外部からの読み込み（DESIGN.md 4.2）。<script src>・<link href>・@import・url(http…)・<img src> の外部の URL"""
    found = []
    sk = _skeleton(doc)
    def attr(tag, name):
        m = re.search(rf"""\s{name}\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", tag, re.I)
        return None if not m else (m.group(1) if m.group(1) is not None else m.group(2) if m.group(2) is not None else m.group(3))
    for kind, tagname, an in [("<script src>", "script", "src"), ("<link href>", "link", "href"), ("<img src>", "img", "src")]:
        for t in re.finditer(rf"<{tagname}\b[^>]*>", sk, re.I):
            u = attr(t.group(0), an)
            if not u or not re.match(EXT, u.strip(), re.I):
                continue
            if tagname == "link":
                rel = (attr(t.group(0), "rel") or "").lower().split()
                if set(rel) & {"canonical", "alternate"}:
                    continue
            found.append(f"{kind} {u.strip()}")
    nocomment = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    css = "\n".join(strip_css_comments(x) for x in re.findall(r"<style[^>]*>(.*?)</style>", nocomment, re.S))
    styles = css + "\n" + "\n".join(a or b for a, b in re.findall(r"\sstyle=\"([^\"]*)\"|\sstyle='([^']*)'", sk))
    for m in re.finditer(rf"""@import\s+(?:url\(\s*)?["']?({EXT}[^"')\s;]+)""", styles, re.I):
        found.append(f"@import {m.group(1)}")
    for m in re.finditer(rf"""(?<!@import )url\(\s*["']?({EXT}[^"')\s]+)""", styles, re.I):
        found.append(f"url() {m.group(1)}")
    return found

SELFTEST_HYOKI_OK = """<html lang="ja"><head><title>R7 の見本</title><style>
:root{--fw-b:700}
.a{font-weight:400}.b{font-weight:700}.c{font-weight:800}.d{font-weight:bold}.e{font-weight:normal}.f{font-weight:inherit}.g{font-weight:var(--fw-b)}
.h{font:700 16px/1.6 sans-serif}.i{font:inherit}.j{background:url(data:image/png;base64,AAAA)}
</style><script src="vendor/chart.js"></script><script>var s = "▲5 +80 くわしく"; x.innerHTML = '<a target="_blank" href="x">a</a>';</script></head><body>
<!-- ▲5 +80 こちら -->
<p>歳出 2,566千円 増。歳入 △1,531千円 減。原典の表では▲を負の値の印に使っている。</p>
<p>R7年度・R8.3（R＝令和）。<a href="https://github.com/kken78/hino-portal?q=+1">GitHub</a> https://example.jp/?a=+1</p>
<p>原典の表記は <q>▲1,531千円</q> <q cite="x">前年比 +3</q>。計 ＝ 本体 ＋３ ＋ 100</p>
<p><code>x = a +1</code></p><pre>+2</pre><table><tr><td>+</td><td>5</td></tr></table>
<p style="font-weight:700">太字</p><img src="og.png" alt="見本">
<a href="https://www.town.shiga-hino.lg.jp/" target="_blank" rel="noopener">日野町ホームページ<span class="v">（新しいタブで開きます）</span></a>
<a href="https://github.com/kken78" target="_blank" aria-label="kken78（GitHub。新しいタブで開きます）">kken78</a>
<a href="https://github.com/kken78" target="_blank">kken78<svg role="img" aria-label="新しいタブで開きます"></svg></a>
</body></html>"""

SELFTEST_HYOKI_NG = [
    ("増減の印 ▲ と数字", "hyoki", "<p>差 ▲1,531千円</p>"),
    ("増減の印 ▲ と「増」", "hyoki", "<p>2,566千円 ▲ 増</p>"),
    ("増減の印 ▼ と「減」", "hyoki", "<td>▼減</td>"),
    ("増減の印 ↑ と数字", "hyoki", "<p>↑12人</p>"),
    ("増減の印（alt の字）", "hyoki", "<img src=\"a.png\" alt=\"▼3人\">"),
    ("+ と数字", "hyoki", "<p>前の月から +80人</p>"),
    ("<q> の外の ▲ と数字", "hyoki", "<p><q>▲1</q> ▲2千円</p>"),
    ("くわしく", "hyoki", "<a href=\"a.html\">くわしく</a>"),
    ("こちら", "hyoki", "<a href=\"a.html\">こちら</a>"),
    ("前年比", "hyoki", "<p>前年比 3%</p>"),
    ("前年度比", "hyoki", "<p>前年度比 3%</p>"),
    ("前回比", "hyoki", "<p aria-label=\"前回比\">x</p>"),
    ("target=_blank に新しいタブの字が無い", "hyoki", "<a href=\"https://github.com/\" target=\"_blank\">GitHub</a>"),
    ("R＋数字の年度があり R＝令和 の注が無い", "hyoki", "<th>R7年度</th><th>R8</th>"),
    ("R＋数字〜 があり注が無い", "hyoki", "<p>R3〜R8</p>"),
    ("太さ 600", "weight", "<style>.a{font-weight:600}</style>"),
    ("太さ 500（style 属性）", "weight", "<p style=\"font-weight:500\">x</p>"),
    ("太さ 900", "weight", "<style>.a{font-weight:900}</style>"),
    ("太さ bolder", "weight", "<style>.a{font-weight:bolder}</style>"),
    ("太さ lighter", "weight", "<style>.a{font-weight:lighter}</style>"),
    ("太さ 300", "weight", "<style>.a{font-weight:300}</style>"),
    ("太さ 600 のトークン", "weight", "<style>:root{--fw:600}.a{font-weight:var(--fw)}</style>"),
    ("太さ 600（font の一括指定）", "weight", "<style>.a{font:600 16px/1.6 sans-serif}</style>"),
    ("外部の <script src>", "external", "<script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js\"></script>"),
    ("外部の <link href>", "external", "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Noto+Sans+JP\">"),
    ("外部の @import", "external", "<style>@import url(\"https://fonts.googleapis.com/css2?family=Noto+Sans+JP\");</style>"),
    ("外部の url()", "external", "<style>.a{background:url(https://example.jp/a.png)}</style>"),
    ("外部の <img src>（// で始まる）", "external", "<img src=\"//example.jp/a.png\" alt=\"見本\">"),
]

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

# 共通の部品も <title> も無いページ（議会系のページの形）。既定では4種の問題が出て、--no-shared では出ない
SELFTEST_NOSHARED = '<html lang="ja"><head><title>日野町議会</title><style>body{font-size:16px}</style></head><body><p>本文</p></body></html>'
SELFTEST_SHARED_KINDS = ["<title> の形が違う", "portal-shared:css のブロックが無い",
                         "portal-shared:header のブロックが無い", "portal-shared:footer のブロックが無い"]

def selftest_options():
    """既定で文字の検査が動くこと（--fonts は互換の指定）、--no-shared で4種の検査が外れること、
    --hyoki で表記と太さの検査が加わること、外部からの読み込みが既定は警告で --strict-external では誤りになることを見本で確かめる"""
    bad = 0
    for argv, want in [(["a.html"], (True, True, False, False)), (["--fonts", "a.html"], (True, True, False, False)),
                       (["--no-shared", "a.html"], (True, False, False, False)), (["--fonts", "--no-shared", "a.html"], (True, False, False, False)),
                       (["--hyoki", "a.html"], (True, True, True, False)), (["--strict-external", "--no-shared", "a.html"], (True, False, False, True))]:
        o = parse_args(argv)
        got = (o["fonts"], o["shared_parts"], o["hyoki"], o["strict_external"])
        if got == want and o["files"] == ["a.html"]:
            print(f"指定 {' '.join(argv)}：文字の検査 {'あり' if got[0] else 'なし'}、共通の部品の検査 {'あり' if got[1] else 'なし'}、"
                  f"表記と太さの検査 {'あり' if got[2] else 'なし'}、外部からの読み込み {'誤り' if got[3] else '警告'}（正しい）")
        else:
            bad += 1
            print(f"指定 {' '.join(argv)}：読み取りが見本と違う {o}（誤り）")
    # 既定（指定なし）の check_doc で、12px の文字が誤りになる
    ps, _ = check_doc('<html lang="ja"><head><style>.a{font-size:12px}</style></head><body></body></html>', HERE)
    if any("12px で 14px 未満" in p for p in ps):
        print("既定の検査：12px の文字を誤りにした（正しい）")
    else:
        bad += 1
        print("既定の検査：12px の文字を誤りにしなかった（誤り）")
    # 共通の部品の無いページ。既定では4種の問題、--no-shared では問題なし
    ps, _ = check_doc(SELFTEST_NOSHARED, HERE)
    kinds = [k for k in SELFTEST_SHARED_KINDS if any(p.startswith(k) for p in ps)]
    if len(kinds) == len(SELFTEST_SHARED_KINDS) and len(ps) == len(SELFTEST_SHARED_KINDS):
        print(f"共通の部品の無いページ（既定）：問題 {len(ps)} 件、4種とも出た（正しい）")
    else:
        bad += 1
        print(f"共通の部品の無いページ（既定）：問題が見本と違う {ps}（誤り）")
    ps, _ = check_doc(SELFTEST_NOSHARED, HERE, shared_parts=False)
    if not ps:
        print("共通の部品の無いページ（--no-shared）：問題なし（正しい）")
    else:
        bad += 1
        print(f"共通の部品の無いページ（--no-shared）：問題が出た {ps}（誤り）")
    ps, _ = check_doc(SELFTEST_NOSHARED.replace("16px", "12px"), HERE, shared_parts=False)
    if len(ps) == 1 and "14px 未満" in ps[0]:
        print("共通の部品の無いページ（--no-shared）の 12px：文字の問題だけが出た（正しい）")
    else:
        bad += 1
        print(f"共通の部品の無いページ（--no-shared）の 12px：問題が見本と違う {ps}（誤り）")
    # 表記と太さは --hyoki を付けたときだけ。外部からの読み込みは既定で警告、--strict-external で誤り
    ng = SELFTEST_NOSHARED.replace("<p>本文</p>", "<p>▲5人</p>").replace("16px", "16px;font-weight:600")
    ext = SELFTEST_NOSHARED.replace("</head>", '<script src="https://cdn.jsdelivr.net/npm/papaparse@5.4.1/papaparse.min.js"></script></head>')
    for name, args, want_p, want_w in [
        ("▲5人と太さ 600 のページ（--hyoki なし）", dict(doc=ng), 0, 0),
        ("▲5人と太さ 600 のページ（--hyoki）", dict(doc=ng, hyoki=True), 2, 0),
        ("CDN の <script src> のページ（既定）", dict(doc=ext), 0, 1),
        ("CDN の <script src> のページ（--strict-external）", dict(doc=ext, strict_external=True), 1, 0)]:
        ps, ws = check_doc(args.pop("doc"), HERE, shared_parts=False, **args)
        if (len(ps), len(ws)) == (want_p, want_w):
            print(f"{name}：誤り {len(ps)} 件、警告 {len(ws)} 件（正しい）")
        else:
            bad += 1
            print(f"{name}：誤り {len(ps)} 件・警告 {len(ws)} 件で、見本の 誤り {want_p} 件・警告 {want_w} 件と違う {ps} {ws}（誤り）")
    return bad, 14

def selftest():
    bad = 0
    ok = font_problems(SELFTEST_OK)
    if ok:
        bad += 1
        print("通る見本：")
        for p in ok:
            print(f"  - {p}")
        print("通る見本で問題が出た（誤り）")
    else:
        print("通る見本（文字の大きさ）：問題なし（正しい）")
    for name, frag in SELFTEST_NG:
        ps = font_problems(f"<html lang=\"ja\"><head></head><body>{frag}</body></html>")
        if ps:
            print(f"通らない見本「{name}」：問題 {len(ps)} 件（正しい）　{ps[0]}")
        else:
            bad += 1
            print(f"通らない見本「{name}」：問題が出なかった（誤り）")
    # 表記・太さ・外部からの読み込み
    ok = hyoki_problems(SELFTEST_HYOKI_OK) + weight_problems(SELFTEST_HYOKI_OK) + external_findings(SELFTEST_HYOKI_OK)
    if ok:
        bad += 1
        print("通る見本（表記・太さ・外部からの読み込み）で問題が出た（誤り）：")
        for p in ok:
            print(f"  - {p}")
    else:
        print("通る見本（表記・太さ・外部からの読み込み）：問題なし（正しい）")
    fn = {"hyoki": hyoki_problems, "weight": weight_problems, "external": external_findings}
    for name, kind, frag in SELFTEST_HYOKI_NG:
        ps = fn[kind](f"<html lang=\"ja\"><head></head><body>{frag}</body></html>")
        if len(ps) == 1:
            print(f"通らない見本「{name}」：問題 {len(ps)} 件（正しい）　{ps[0]}")
        else:
            bad += 1
            print(f"通らない見本「{name}」：問題 {len(ps)} 件で、見本の1件と違う {ps}（誤り）")
    obad, on = selftest_options()
    bad += obad
    total = 1 + len(SELFTEST_NG) + 1 + len(SELFTEST_HYOKI_NG) + on
    print(f"見本 {total} 件のうち、見本どおりでないもの {bad} 件")
    return 1 if bad else 0

def parse_args(argv):
    o = {"selftest": False, "shared": HERE, "fonts": True, "shared_parts": True, "hyoki": False,
         "strict_external": False, "files": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--selftest":
            o["selftest"] = True; i += 1
        elif a == "--fonts":
            i += 1  # 互換の指定。文字の大きさの検査は既定で行う
        elif a == "--no-shared":
            o["shared_parts"] = False; i += 1
        elif a == "--hyoki":
            o["hyoki"] = True; i += 1
        elif a == "--strict-external":
            o["strict_external"] = True; i += 1
        elif a == "--shared":
            o["shared"] = argv[i + 1]; i += 2
        else:
            o["files"].append(a); i += 1
    return o

def main(argv):
    o = parse_args(argv)
    if o["selftest"]:
        return selftest()
    shared, fonts, files = o["shared"], o["fonts"], o["files"]
    if not files:
        print(__doc__); return 2
    bad = 0
    for f in files:
        ps, ws = check(f, shared, fonts, o["shared_parts"], o["hyoki"], o["strict_external"])
        if ps:
            bad += 1
            print(f"{f}：問題 {len(ps)} 件")
            for p in ps:
                print(f"  - {p}")
        else:
            seen = "共通の部品は正本と同じ。文字の大きさは 14px 以上" if o["shared_parts"] else "文字の大きさは 14px 以上"
            if o["hyoki"]:
                seen += "。表記と太さに問題なし"
            if not o["shared_parts"]:
                seen += "（--no-shared のため、<title> の形と共通の部品は見ていない）"
            print(f"{f}：{seen}")
        # 警告の行は「  - 」で始めない（各リポジトリの CI が「  - 」の行を問題として数えているため）
        for w in ws:
            print(f"  警告：{w}（--strict-external を付けると誤りになる）")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
