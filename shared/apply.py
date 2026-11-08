#!/usr/bin/env python3
"""共通の部品を hino-portal/shared の正本で置き換える（DESIGN.md 9.2）。

使い方：
  python3 shared/apply.py [--check] [--shared <正本のフォルダ>] <HTML ファイル>...
  正本のフォルダを省くと、このファイルと同じフォルダを使う。

各ファイルの <!-- portal-shared:〈名前〉 start --> … <!-- portal-shared:〈名前〉 end --> の中を、正本で置き換える。
名前と正本：
  css            shell.css（<style> と </style> の間に、そのまま入れる）
  header         header.html
  siblings       siblings-plan.html か siblings-stat.html（いまのブロックの aria-label で選ぶ。合わなければリンクの重なりで選ぶ）
  siblings-plan  siblings-plan.html
  siblings-stat  siblings-stat.html
  footer         footer.html
ページごとに違うところは、置き換えのあとも元の値を保つ：
  header    分野のナビの aria-current="page" を付けたリンク（リンクの文字と href で探して、同じリンクに付け直す）
  siblings  <span aria-current="page">題</span> にしたいまのページ（正本の <a href="…">題</a> を同じ形に替える）
  footer    {{…}} を埋めた中身。項目（dt）ごとに、ページの dd をそのまま残す。正本の dd の先頭にある {{…}} を含まない <p>
            （「このページについて」の位置づけの文、「注意」の固定の文）だけを正本の字にする。項目の順は正本の順にし、
            ページに無い項目は足さない（当てはまらない項目は飛ばしてよい。DESIGN.md 2.5）。正本に無い項目は残して末尾に置く
正本と同じとき（check.py と同じ比べ方。空白の違いは見ない）は書き換えない。ブロックの前後の空白と改行は、元のものを保つ。

--check：書き換えずに、違うブロックの一覧だけを出す。
終了コード：0 は書き換えた（一覧を出す）か、書き換えるものが無かった。--check で違いがあれば 1。
            元の値を保てない（いまの分野・ページが正本に無いなど）ファイルがあれば、そのファイルは書き換えずに 2。
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True  # shared/ に __pycache__ を作らない
sys.path.insert(0, HERE)
from check import norm  # noqa: E402  比べ方を check.py とそろえる

BLOCK = re.compile(r"(<!-- portal-shared:([\w-]+) start -->)(.*?)(<!-- portal-shared:\2 end -->)", re.S)

class Keep(Exception):
    """元の値を保てないので、そのファイルを書き換えない"""

def read(shared, name):
    with open(os.path.join(shared, name), encoding="utf-8") as f:
        return f.read()

def wrap_ws(old, new_core):
    """old の前後の空白を保って、中身を new_core にする"""
    lead = re.match(r"\s*", old).group(0)
    trail = re.search(r"\s*$", old).group(0)
    return lead + new_core.strip() + trail

def apply_css(old, shared):
    want = read(shared, "shell.css")
    m = re.search(r"(<style[^>]*>)(.*?)(</style>)", old, re.S)
    if m and norm(m.group(2)) == norm(want):
        return old
    if not m:
        return wrap_ws(old, "<style>" + want + "</style>")
    return old[:m.start(2)] + wrap_ws(m.group(2), want) + old[m.end(2):]

def apply_header(old, shared):
    want = read(shared, "header.html")
    got = norm(old)
    plain, n = re.subn(r' aria-current="page"', "", got)
    if n <= 1 and plain == norm(want):
        return old
    new = want.strip()
    cur = None
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", old, re.S):
        if 'aria-current="page"' in m.group(1):
            href = re.search(r'href="([^"]*)"', m.group(1))
            first = m.group(1).lstrip().startswith('aria-current="page"')
            cur = (href.group(1) if href else None, m.group(2).strip(), first)
            break
    if cur:
        nav = re.search(r'<nav class="portal-areas"[^>]*>.*?</nav>', new, re.S)
        if not nav:
            raise Keep("正本の header に分野のナビ（nav.portal-areas）が無い")
        links = list(re.finditer(r"<a\b([^>]*)>(.*?)</a>", nav.group(0), re.S))
        hit = [l for l in links if l.group(2).strip() == cur[1] and f'href="{cur[0]}"' in l.group(1)] or \
              [l for l in links if l.group(2).strip() == cur[1]] or \
              [l for l in links if cur[0] and f'href="{cur[0]}"' in l.group(1)]
        if not hit:
            raise Keep(f"いまの分野「{cur[1]}」（{cur[0]}）が正本の分野のナビに無い")
        l = hit[0]
        # 属性の位置は元のページの書き方に合わせる（<a aria-current="page" href=…> か <a href=… aria-current="page">）
        if cur[2]:
            a = l.group(0).replace("<a ", '<a aria-current="page" ', 1)
        else:
            a = re.sub(r"^(<a\b[^>]*?)>", r'\1 aria-current="page">', l.group(0), count=1)
        s = nav.start() + l.start()
        new = new[:s] + a + new[s + len(l.group(0)):]
    return wrap_ws(old, new)

SIBLINGS = {"siblings-plan": "siblings-plan.html", "siblings-stat": "siblings-stat.html"}

def apply_siblings(old, shared, name):
    if name in SIBLINGS:
        names = [SIBLINGS[name]]
    else:
        names = list(SIBLINGS.values())
    wants = {n: read(shared, n) for n in names}
    got = norm(old)
    # いまのページの題
    cur = re.search(r'<span aria-current="page">([^<]+)</span>', old)
    def marked(w):
        if not cur:
            return w
        t = cur.group(1)
        a = re.search(rf'<a href="[^"]+">{re.escape(t)}</a>', w)
        if not a:
            return None
        return w[:a.start()] + f'<span aria-current="page">{t}</span>' + w[a.end():]
    for w in wants.values():
        if got == norm(w) or (marked(w) is not None and got == norm(marked(w))):
            return old
    # どちらの正本か
    if len(names) == 1:
        pick = names[0]
    else:
        lab = re.search(r'aria-label="([^"]*)"', old)
        pick = None
        if lab:
            for n, w in wants.items():
                if f'aria-label="{lab.group(1)}"' in w:
                    pick = n
        if pick is None:
            hrefs = set(re.findall(r'href="([^"]+)"', old))
            score = {n: len(hrefs & set(re.findall(r'href="([^"]+)"', w))) for n, w in wants.items()}
            best = max(score.values())
            picks = [n for n, s in score.items() if s == best]
            if best == 0 or len(picks) > 1:
                raise Keep("siblings のブロックが siblings-plan.html・siblings-stat.html のどちらに当たるか決められない")
            pick = picks[0]
    new = marked(wants[pick].strip())
    if new is None:
        raise Keep(f"いまのページ「{cur.group(1)}」が正本 {pick} に無い")
    return wrap_ws(old, new)

def _pairs(fragment):
    """<dt>…</dt><dd>…</dd> の組。dd は次の <dt> か </dl> の前まで"""
    return [(m.group(1), m.group(2)) for m in
            re.finditer(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>(?=\s*(?:<dt>|</dl>))", fragment, re.S)]

def apply_footer(old, shared):
    want = read(shared, "footer.html").strip()
    tpairs = _pairs(want)
    first = want.index("<dt>")
    last = want.rindex("</dd>") + len("</dd>")
    prefix, suffix = want[:first], want[last:]
    sep = re.search(r"</dd>(\s*)<dt>", want).group(1)
    order = [norm(t) for t, _ in tpairs]
    tdd = {norm(t): d for t, d in tpairs}
    opairs = _pairs(old)
    if not opairs:
        raise Keep("footer のブロックに <dt>…</dt><dd>…</dd> の組が無い")
    known = sorted([p for p in opairs if norm(p[0]) in order], key=lambda p: order.index(norm(p[0])))
    unknown = [p for p in opairs if norm(p[0]) not in order]
    items = []
    for dt, dd in known + unknown:
        key = norm(dt)
        if key in tdd:
            # 正本の dd の先頭の、{{…}} を含まない <p> は固定の文。ページの dd の先頭の同じ数の <p> を、正本の字にする
            fixed = []
            rest = tdd[key]
            while True:
                m = re.match(r"\s*(<p>.*?</p>)", rest, re.S)
                if not m or "{{" in m.group(1):
                    break
                fixed.append(m.group(1))
                rest = rest[m.end():]
            body = dd
            if fixed:
                ps = []
                for _ in fixed:
                    m = re.match(r"\s*<p>.*?</p>", body, re.S)
                    if not m:
                        break
                    ps.append(m.group(0))
                    body = body[m.end():]
                if len(ps) < len(fixed):
                    body = dd  # ページの dd が <p> で始まっていないときは、固定の文を前に足す
                body = "".join(fixed) + body
            items.append(f"<dt>{key}</dt><dd>{body}</dd>")
        else:
            items.append(f"<dt>{dt}</dt><dd>{dd}</dd>")
    new = prefix + sep.join(items) + suffix
    if norm(new) == norm(old):
        return old
    return wrap_ws(old, new)

def apply_doc(doc, shared):
    """戻り値は (新しい文書, 置き換えたブロックの名前の一覧, 知らない名前の一覧)"""
    changed, unknown = [], []
    def repl(m):
        start, name, inner, end = m.group(1), m.group(2), m.group(3), m.group(4)
        if name == "css":
            new = apply_css(inner, shared)
        elif name == "header":
            new = apply_header(inner, shared)
        elif name in ("siblings", "siblings-plan", "siblings-stat"):
            new = apply_siblings(inner, shared, name)
        elif name == "footer":
            new = apply_footer(inner, shared)
        else:
            unknown.append(name)
            return m.group(0)
        if new != inner:
            changed.append(name)
        return start + new + end
    return BLOCK.sub(repl, doc), changed, unknown

def main(argv):
    check_only, shared, files = False, HERE, []
    i = 0
    while i < len(argv):
        if argv[i] == "--check":
            check_only = True; i += 1
        elif argv[i] == "--shared":
            shared = argv[i + 1]; i += 2
        else:
            files.append(argv[i]); i += 1
    if not files:
        print(__doc__); return 2
    changed_files, kept = [], 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            doc = fh.read()
        try:
            new, changed, unknown = apply_doc(doc, shared)
        except Keep as e:
            kept += 1
            print(f"{f}：書き換えない（元の値を保てない：{e}）")
            continue
        for u in unknown:
            print(f"{f}：portal-shared:{u} は知らない名前なので、そのままにした")
        if not changed:
            print(f"{f}：正本と同じ")
            continue
        changed_files.append(f)
        if check_only:
            print(f"{f}：正本と違う（{'・'.join(changed)}）")
        else:
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new)
            print(f"{f}：書き換えた（{'・'.join(changed)}）")
    verb = "正本と違うファイル" if check_only else "書き換えたファイル"
    print(f"{verb} {len(changed_files)} 本（{len(files)} 本のうち）" + (f"。元の値を保てず書き換えなかったファイル {kept} 本" if kept else ""))
    if kept:
        return 2
    return 1 if (check_only and changed_files) else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
