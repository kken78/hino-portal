#!/usr/bin/env python3
"""共通の部品が hino-portal/shared の正本と同じかを確かめる（DESIGN.md 9.1）。

使い方：
  python3 shared/check.py [--shared <正本のフォルダ>] <HTML ファイル>...
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
終了コード：問題が無ければ 0、あれば 1（問題をファイルごとに出す）。外部には何も読みに行かない。
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

def check(path, shared):
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
    return problems

def main(argv):
    shared = HERE
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == "--shared":
            shared = argv[i + 1]; i += 2
        else:
            files.append(argv[i]); i += 1
    if not files:
        print(__doc__); return 2
    bad = 0
    for f in files:
        ps = check(f, shared)
        if ps:
            bad += 1
            print(f"{f}：問題 {len(ps)} 件")
            for p in ps:
                print(f"  - {p}")
        else:
            print(f"{f}：共通の部品は正本と同じ")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
