"""tools/bundle.py の試験（標準ライブラリの unittest）。

  python3 -m unittest discover -s tools -p 'test_*.py'
"""
import argparse
import contextlib
import datetime
import hashlib
import io
import os
import sys
import tempfile
import unittest
import urllib.error
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bundle  # noqa: E402

P = bundle.PORTAL_DIR
C = bundle.COUNCIL_DIR
DESTS = {
    "hino-portal": P,
    "shiga-hino-plans": f"{P}/shiga-hino-plans",
    "hino-shiryo": f"{P}/hino-shiryo",
    "council-dashboard": f"{P}/council-dashboard",
    "hino-council-search": C,
}


class RewriteTest(unittest.TestCase):
    def rw(self, text, base, html=False):
        return bundle.rewrite_urls(text, base, DESTS, protect_html=html)

    def test_folder_gets_index(self):
        self.assertEqual(self.rw('href="https://kken78.github.io/hino-portal/"', P), 'href="index.html"')
        self.assertEqual(self.rw('href="https://kken78.github.io/hino-portal"', P), 'href="index.html"')
        self.assertEqual(self.rw("'https://kken78.github.io/shiga-hino-plans/'", P),
                         "'shiga-hino-plans/index.html'")

    def test_subpath_and_folder_without_slash(self):
        self.assertEqual(self.rw("https://kken78.github.io/shiga-hino-plans/plans/sogo6.html", P),
                         "shiga-hino-plans/plans/sogo6.html")
        self.assertEqual(self.rw("https://kken78.github.io/shiga-hino-plans/plans", P),
                         "shiga-hino-plans/plans/index.html")

    def test_hash_and_query_kept(self):
        self.assertEqual(self.rw("https://kken78.github.io/hino-portal/#g-plan", f"{P}/hino-shiryo"),
                         "../index.html#g-plan")
        self.assertEqual(
            self.rw("https://kken78.github.io/hino-council-search/#thread=1&focus=0", f"{P}/council-dashboard"),
            f"../../{C}/index.html#thread=1&focus=0")
        self.assertEqual(self.rw("https://kken78.github.io/hino-shiryo/?q=a#x", P), "hino-shiryo/index.html?q=a#x")

    def test_from_deeper_page(self):
        self.assertEqual(self.rw("https://kken78.github.io/hino-portal/", f"{P}/shiga-hino-plans/plans"),
                         "../../index.html")
        self.assertEqual(self.rw("https://kken78.github.io/hino-portal/", C), f"../{P}/index.html")

    def test_js_string_concat(self):
        self.assertEqual(self.rw("u='https://kken78.github.io/hino-council-search/#q='+q", f"{P}/council-dashboard"),
                         f"u='../../{C}/index.html#q='+q")

    def test_unknown_and_other_hosts_untouched(self):
        for s in ("https://kken78.github.io/other-repo/", "https://github.com/kken78/hino-portal",
                  "https://www.town.shiga-hino.lg.jp/0000002185.html", "https://kken78.github.io/"):
            self.assertEqual(self.rw(s, P), s)

    def test_trailing_punctuation(self):
        self.assertEqual(self.rw("見る：https://kken78.github.io/hino-portal/.", P), "見る：index.html.")

    def test_meta_and_canonical_protected(self):
        src = ('<link rel="canonical" href="https://kken78.github.io/hino-portal/">'
               '<meta property="og:url" content="https://kken78.github.io/hino-portal/">'
               '<a href="https://kken78.github.io/hino-portal/">t</a>')
        out = self.rw(src, P, html=True)
        self.assertIn('<link rel="canonical" href="https://kken78.github.io/hino-portal/">', out)
        self.assertIn('content="https://kken78.github.io/hino-portal/"', out)
        self.assertIn('<a href="index.html">', out)


class SelectTest(unittest.TestCase):
    def test_default_exclude(self):
        files = {p: b"" for p in (
            "index.html", "data.js", "data/a.csv", ".github/workflows/x.yml", ".claude/settings.json", ".nojekyll",
            "README.md", "DESIGN.md", "tools/x.py", "build.py", "inputs.lock.json", "data/watch.tsv",
            "sources/2025-10.pdf", "LICENSE", "LICENSE-DATA.md", "vendor/LICENSE-chartjs.md", "vendor/chart.umd.js",
            "shared/__pycache__/check.cpython-313.pyc")}
        kept = set(bundle.select(files))
        self.assertEqual(kept, {"index.html", "data.js", "data/a.csv", "LICENSE", "LICENSE-DATA.md",
                                "vendor/LICENSE-chartjs.md", "vendor/chart.umd.js"})

    def test_extra_exclude(self):
        files = {"plans/_charttest.html": b"", "plans/sogo6.html": b""}
        self.assertEqual(set(bundle.select(files, ["plans/_*"])), {"plans/sogo6.html"})


class InjectTest(unittest.TestCase):
    def test_band_and_style(self):
        import datetime
        band = bundle.band_html(datetime.date(2026, 11, 11), datetime.date(2026, 11, 10))
        self.assertIn("<p>手元版（2026年11月11日作成）　公開版の2026年11月10日時点と同じ内容です。</p>", band)
        self.assertNotIn("インターネット", band)
        out = bundle.inject('<html><head><title>t</title></head><body class="x"><p>a</p></body></html>', band)
        self.assertLess(out.index('id="temoto-style"'), out.index("</head>"))
        self.assertTrue(out.split('<body class="x">', 1)[1].startswith('<div class="temoto-band"'))

    def test_extra_css_inside_style(self):
        out = bundle.inject("<html><head></head><body></body></html>", "B", ".x::after{content:none}")
        self.assertIn('.x::after{content:none}</style></head>', out)

    def test_no_body(self):
        with self.assertRaises(bundle.BundleError):
            bundle.inject("<html><head></head></html>", "B")

    def test_band_font_size_not_below_14(self):
        self.assertIn("--portal-fs-sub:14px", bundle.BAND_STYLE)
        self.assertNotRegex(bundle.BAND_STYLE, r"font-size:\s*(1[0-3]|[0-9])px")


class NoMarkTest(unittest.TestCase):
    def test_css(self):
        css = bundle.no_mark_css([{"selector": ".tlcap", "note_before": "#sessionTL", "note": 'a"b'}])
        self.assertIn(".tlcap::after{content:none!important}", css)
        self.assertIn('#sessionTL::before{content:"a\\"b";display:block', css)
        self.assertNotRegex(css, r"font-size:\s*(1[0-3]|[0-9])px")

    def test_note_style(self):
        css = bundle.no_mark_css([{"selector": ".bchip", "note_before": "#bulletinList", "note": "x",
                                   "note_style": "color:var(--ink-2);margin:-12px 0 4px"}])
        self.assertIn("grid-column:1/-1", css)
        self.assertTrue(css.endswith("color:var(--ink-2);margin:-12px 0 4px}"))
        with self.assertRaises(bundle.BundleError):
            bundle.no_mark_css([{"selector": ".a", "note_before": "#a", "note": "x", "note_style": "}x{"}])

    def test_empty(self):
        self.assertEqual(bundle.no_mark_css([]), "")

    def test_bad_selector(self):
        with self.assertRaises(bundle.BundleError):
            bundle.no_mark_css([{"selector": ".a{}</style>"}])
        with self.assertRaises(bundle.BundleError):
            bundle.no_mark_css([{"selector": ".a", "note_before": "#a b", "note": "x"}])


class CouncilPdfTest(unittest.TestCase):
    def test_map(self):
        meetings = [{"id": "0000001", "pdfs": [{"url": "https://h/c/1/4nitime.pdf"}]},
                    {"id": "0000002", "pdfs": [{"url": "https://h/c/2/4nitime.pdf"}]}]
        toc = [{"id": "0000001", "pdfs": [{"url": "https://h/c/1/4nitime.pdf"}, {"url": ""}]}]
        m = bundle.council_pdf_map(meetings, toc)
        self.assertEqual(m, {"https://h/c/1/4nitime.pdf": "議事録本体/0000001_4nitime.pdf",
                             "https://h/c/2/4nitime.pdf": "議事録本体/0000002_4nitime.pdf"})


class ForbiddenTest(unittest.TestCase):
    def test_kinds(self):
        f = bundle.forbidden_reason
        self.assertIsNotNone(f("x/autorun.inf", b"[autorun]"))
        self.assertIsNotNone(f("a.exe", b""))
        self.assertIsNotNone(f("a.dat", b"MZ\x90\x00"))
        self.assertIsNotNone(f("a.bin", b"\x7fELF"))
        self.assertIsNotNone(f("a.xlsm", b""))
        self.assertIsNone(f("index.html", b"<html>"))
        self.assertIsNone(f("data.js", b"var a=1"))
        self.assertIsNone(f("a.pdf", b"%PDF-1.7"))

    def test_macro_in_ooxml(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("[Content_Types].xml", "x")
            z.writestr("xl/vbaProject.bin", "x")
        self.assertIn("マクロ", bundle.forbidden_reason("a.xlsx", buf.getvalue()))
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("[Content_Types].xml", "x")
        self.assertIsNone(bundle.forbidden_reason("a.xlsx", buf.getvalue()))

    def test_macro_in_ole(self):
        data = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64 + "_VBA_PROJECT".encode("utf-16-le")
        self.assertIn("マクロ", bundle.forbidden_reason("a.xls", data))


class LinkCheckTest(unittest.TestCase):
    FILES = {f"{P}/index.html", f"{P}/hino-shiryo/index.html", f"{P}/hino-shiryo/data/index.js", f"{C}/index.html"}
    DIRS = {P, f"{P}/hino-shiryo", f"{P}/hino-shiryo/data", C}

    def exists(self, p):
        return True if p in self.FILES else ("dir" if p in self.DIRS else False)

    def test_refs(self):
        c = lambda page, v: bundle.check_ref(page, v, self.exists)  # noqa: E731
        page = f"{P}/hino-shiryo/index.html"
        self.assertIsNone(c(page, "data/index.js"))
        self.assertIsNone(c(page, "../index.html#g-plan"))
        self.assertIsNone(c(page, f"../../{C}/index.html#q=1"))
        self.assertIsNone(c(page, "data/index.js?v=1"))
        self.assertIsNone(c(page, "#top"))
        self.assertIsNone(c(page, "https://www.town.shiga-hino.lg.jp/"))
        self.assertIsNone(c(page, "mailto:a@example.com"))
        self.assertEqual(c(page, "data/nai.js"), "ファイルが無い")
        self.assertIn("フォルダ", c(page, "data/"))
        self.assertIn("フォルダ", c(page, "data"))
        self.assertIn("一式の外", c(page, "../../../x.html"))
        self.assertIn("/ で始まる", c(page, "/hino-portal/"))

    def test_percent_encoded(self):
        self.assertIsNone(bundle.check_ref(f"{P}/index.html", "../%E6%97%A5%E9%87%8E%E7%94%BA%E8%AD%B0%E4%BC%9A_"
                                           "%E4%BC%9A%E8%AD%B0%E9%8C%B2%E6%A4%9C%E7%B4%A2/index.html", self.exists))

    def test_collect_refs(self):
        refs = bundle.collect_refs(
            '<link rel="canonical" href="https://x/"><link rel="stylesheet" href="a.css">'
            '<script src="b.js"></script><script>var s="<a href=\'c.html\'>";</script>'
            '<img srcset="d.png 1x, e.png 2x"><div style="background:url(f.png)"></div>'
            '<style>@import "g.css"; .x{background:url(\'h.png\')}</style><a href="i.html">i</a>')
        vals = [r[3] for r in refs]
        self.assertEqual(vals, ["a.css", "b.js", "d.png", "e.png", "f.png", "g.css", "h.png", "i.html"])


class LockTest(unittest.TestCase):
    def test_repo_lock_is_valid(self):
        lock = bundle.load_lock(os.path.join(bundle.REPO_ROOT, "bundle.lock.json"))
        names = [r["name"] for r in lock["repos"]]
        for n in ("hino-portal", "shiga-hino-plans", "hino-plan-dashboard", "hino-zaisei", "hino-shisan",
                  "hino-population", "hino-dashboard", "choisoko-hino-dashboard", "council-dashboard",
                  "hino-shiryo", "hino-council-search"):
            self.assertIn(n, names)
        council = [r for r in lock["repos"] if r["name"] == "hino-council-search"][0]
        self.assertIn(council["make"], bundle.COUNCIL_MAKES)
        for r in lock["repos"]:
            bundle.no_mark_css(r.get("no_mark", []))
        dests = bundle.dest_map(lock["repos"])
        self.assertEqual(dests["hino-portal"], P)
        self.assertEqual(dests["hino-council-search"], C)

    def test_ledgers(self):
        lock = bundle.load_lock(os.path.join(bundle.REPO_ROOT, "bundle.lock.json"))
        led = {r["name"]: r for r in lock["ledgers"]}
        self.assertEqual(led["hino-town-docs"]["use"], "data/sources.tsv")
        self.assertNotIn("hino-town-docs", [r["name"] for r in lock["repos"]])
        for body in ('"ledgers":[{"name":"x","commit":"abc","use":"a"}]',
                     '"ledgers":[{"name":"x","commit":"%s","use":"a","dest":"%s/x"}]' % ("0" * 40, P),
                     '"ledgers":[{"name":"a","commit":"%s","use":"a"}]' % ("0" * 40)):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
                f.write('{"repos":[{"name":"a","commit":"%s","source":".","dest":"%s/a"}],%s}' % ("1" * 40, P, body))
            try:
                with self.assertRaises(bundle.BundleError, msg=body):
                    bundle.load_lock(f.name)
            finally:
                os.unlink(f.name)

    def test_bad_commit(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('{"repos":[{"name":"a","commit":"abc","source":".","dest":"%s/a"}]}' % P)
        try:
            with self.assertRaises(bundle.BundleError):
                bundle.load_lock(f.name)
        finally:
            os.unlink(f.name)


TOWN = "https://www.town.shiga-hino.lg.jp/cmsfiles/contents/"
PDF = b"%PDF-1.4\n%%EOF\n"


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


class LocalRewriteTest(unittest.TestCase):
    """一式に入れたファイルの URL の書き換え（11.4）"""
    A = TOWN + "0000005/5559/R3.9hoseiyosann(tuika)nogaiyou.pdf"
    B = TOWN + "0000001/1791/01.pdf"
    FMAP = {A: f"{P}/原典/資料/yosan/yosan-r3-hosei-09-tsuika.pdf", B: f"{P}/原典/計画/sogo6/honpen-01.pdf"}

    def rw(self, text, base, **kw):
        return bundle.rewrite_local_files(text, base, self.FMAP, **kw)

    def test_html_and_page_kept(self):
        self.assertEqual(self.rw(f'<a href="{self.B}#page=3">p</a>', f"{P}/shiga-hino-plans/plans"),
                         '<a href="../../原典/計画/sogo6/honpen-01.pdf#page=3">p</a>')

    def test_js_data_and_parentheses(self):
        self.assertEqual(self.rw('{"u":"%s","f":"pdf"}' % self.A, f"{P}/hino-shiryo"),
                         '{"u":"../原典/資料/yosan/yosan-r3-hosei-09-tsuika.pdf","f":"pdf"}')
        self.assertEqual(self.rw(f"u='{self.A}'+'#page='+n", f"{P}/hino-zaisei"),
                         "u='../原典/資料/yosan/yosan-r3-hosei-09-tsuika.pdf'+'#page='+n")

    def test_from_council_folder(self):
        self.assertEqual(self.rw(f'"{self.B}"', C), f'"../{P}/原典/計画/sogo6/honpen-01.pdf"')

    def test_exact_match_only(self):
        for s in (self.B + "x", self.B + "/", self.B + "?a=1", self.B.replace("https:", "http:"),
                  self.B[:-4] + "2.pdf", TOWN + "0000001/1791/1.pdf", TOWN + "0000001/1791/001.pdf",
                  self.A.replace("(tuika)", ""),
                  "https://web.archive.org/web/20250416000000id_/" + self.B,
                  "https://example.org/?u=" + self.B):
            self.assertEqual(self.rw(f'"{s}"', P), f'"{s}"', s)

    def test_trailing_punctuation(self):
        self.assertEqual(self.rw(f"（{self.B}）。", P), "（原典/計画/sogo6/honpen-01.pdf）。")
        self.assertEqual(self.rw(f"見る：{self.B}.", P), "見る：原典/計画/sogo6/honpen-01.pdf.")

    def test_known_but_not_bundled_stays(self):
        online, log = [], []
        other = TOWN + "0000008/8534/R8jigyou.pdf"
        out = self.rw(f'<a href="{other}">a</a><a href="{self.B}">b</a>', P,
                      known={other, self.B}, online=online, log=log)
        self.assertIn(f'href="{other}"', out)
        self.assertEqual(online, [other])
        self.assertEqual(log, [(self.B, self.FMAP[self.B])])

    def test_meta_protected(self):
        src = f'<meta property="og:image" content="{self.B}"><a href="{self.B}">a</a>'
        out = self.rw(src, P, protect_html=True)
        self.assertIn(f'content="{self.B}"', out)
        self.assertIn('<a href="原典/計画/sogo6/honpen-01.pdf">', out)

    def test_href_path_escapes(self):
        self.assertEqual(bundle.href_path("原典/a b/%x#y.pdf"), "原典/a%20b/%25x%23y.pdf")


class GentenItemsTest(unittest.TestCase):
    def test_plan_and_doc_paths(self):
        plans = [{"id": "sogo6", "file": "honpen-01.pdf", "url": "u1", "sha256": "AB"},
                 {"id": "kanbatsu", "file": "", "url": "", "sha256": ""}]
        it = bundle.plan_items(plans, "/raw")
        self.assertEqual(len(it), 1)
        self.assertEqual(it[0]["dest"], f"{P}/原典/計画/sogo6/honpen-01.pdf")
        self.assertEqual(it[0]["srcs"], [os.path.join("/raw", "sogo6", "honpen-01.pdf")])
        self.assertEqual(it[0]["sha256"], "ab")
        docs = [{"id": "yosan-r8-gaiyou", "category": "yosan", "url": TOWN + "a/b.PDF", "format": "pdf", "sha256": "x"},
                {"id": "zaisei-r6-shiryo", "category": "zaisei", "url": TOWN + "a/b.xlsx", "format": "xlsx", "sha256": "y"},
                {"id": "kaiken-20260225-page", "category": "kaiken", "url": "https://h/1.html", "format": "html",
                 "sha256": "z"}]
        it = bundle.doc_items(docs, "/d")
        self.assertEqual([x["dest"] for x in it], [f"{P}/原典/資料/yosan/yosan-r8-gaiyou.pdf",
                                                   f"{P}/原典/資料/zaisei/zaisei-r6-shiryo.xlsx"])
        self.assertEqual(it[0]["srcs"], [os.path.join("/d", "yosan-r8-gaiyou.pdf")])

    def test_unsafe_names(self):
        with self.assertRaises(bundle.BundleError):
            bundle.plan_items([{"id": "a", "file": "../x.pdf", "url": "u", "sha256": ""}], "/r")
        with self.assertRaises(bundle.BundleError):
            bundle.doc_items([{"id": "a/b", "category": "c", "url": "u.pdf", "format": "pdf", "sha256": ""}], "/r")

    def test_council_and_town_items(self):
        meta = {"meetings": [{"id": "0000001", "pdfs": [{"url": TOWN + "1/4nitime.pdf"}]}], "toc": []}
        it = bundle.council_items(meta, C, "/c")
        self.assertEqual(it[0]["dest"], f"{C}/議事録本体/0000001_4nitime.pdf")
        self.assertEqual(it[0]["srcs"], [os.path.join("/c", "0000001_4nitime.pdf")])
        t = bundle.town_file_items([TOWN + "7081/hino36web.pdf"], [TOWN + "7949/1_nisikido.JPG", ""],
                                   f"{P}/council-dashboard", "/t")
        self.assertEqual([x["dest"] for x in t], [f"{P}/原典/議会だより/hino36web.pdf",
                                                  f"{P}/council-dashboard/写真/1_nisikido.JPG"])
        self.assertEqual(t[1]["srcs"], [os.path.join("/t", "写真", "1_nisikido.JPG")])

    def test_duplicate_dest(self):
        with self.assertRaises(bundle.BundleError):
            bundle.check_items([{"dest": "a", "url": "1"}, {"dest": "a", "url": "2"}])

    def test_archive_alias(self):
        arc = "https://web.archive.org/web/20250416122618id_/" + TOWN + "0000008/8225/keikaku.pdf"
        rows = [{"id": "jigyo-a", "category": "jigyo", "url": TOWN + "0000008/8225/keikaku.pdf", "format": "pdf",
                 "sha256": "", "archive_url": arc}]
        it = bundle.doc_items(rows, "/d")
        fmap = bundle.file_map([dict(it[0], src="x")])
        self.assertEqual(fmap[arc], f"{P}/原典/資料/jigyo/jigyo-a.pdf")
        out = bundle.rewrite_local_files(f'"{arc}" "{arc.replace("id_/", "/")}"', f"{P}/hino-shiryo", fmap)
        self.assertEqual(out, f'"../原典/資料/jigyo/jigyo-a.pdf" "{arc.replace("id_/", "/")}"')

    def test_file_map_priority(self):
        present = [{"kind": "doc", "url": "u", "dest": "d"}, {"kind": "plan", "url": "u", "dest": "p1"},
                   {"kind": "plan", "url": "u", "dest": "p2"}, {"kind": "council", "url": "c", "dest": "k"}]
        self.assertEqual(bundle.file_map(present), {"u": "p1", "c": "k"})

    def test_read_ledger(self):
        rows = bundle.read_ledger('id\turl\nA\t"x"\n', ("id", "url"), "t")
        self.assertEqual(rows, [{"id": "A", "url": '"x"'}])
        with self.assertRaises(bundle.BundleError):
            bundle.read_ledger("id\n", ("id", "url"), "t")


class ResolveTest(unittest.TestCase):
    def test_present_missing_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            ok, bad, jpg, notjpg = (os.path.join(d, n) for n in ("ok.pdf", "bad.pdf", "a.JPG", "b.JPG"))
            write(ok, PDF)
            write(bad, PDF + b"x")
            write(jpg, b"\xff\xd8\xff\xe0rest")
            write(notjpg, b"<html>not found</html>")
            sha = hashlib.sha256(PDF).hexdigest()
            items = [{"kind": "plan", "url": "1", "srcs": [ok], "sha256": sha, "dest": "a", "label": "1"},
                     {"kind": "plan", "url": "2", "srcs": [bad], "sha256": sha, "dest": "b", "label": "2"},
                     {"kind": "doc", "url": "3", "srcs": [os.path.join(d, "no.pdf"), ok], "sha256": sha,
                      "dest": "c", "label": "3"},
                     {"kind": "doc", "url": "4", "srcs": [os.path.join(d, "no.pdf")], "sha256": sha, "dest": "d",
                      "label": "4"},
                     {"kind": "photo", "url": "5", "srcs": [jpg], "sha256": "", "dest": "e", "label": "5"},
                     {"kind": "photo", "url": "6", "srcs": [notjpg], "sha256": "", "dest": "f", "label": "6"}]
            present, missing, mismatch = bundle.resolve_items(items)
            self.assertEqual([x["url"] for x in present], ["1", "3", "5"])
            self.assertEqual(present[1]["src"], ok)
            self.assertEqual([x["url"] for x in missing], ["4"])
            self.assertEqual([x[0]["url"] for x in mismatch], ["2", "6"])
            self.assertIn("sha256", mismatch[0][1])
            counts = bundle.summary_counts(items, present)
            self.assertEqual(counts["plan"], (2, 1))
            self.assertEqual(counts["council"], (0, 0))
            self.assertEqual(bundle.bundled_state(counts)["議員の写真"], "some")


class ExtraFilesTest(unittest.TestCase):
    def test_only_listed_files_are_copied(self):
        """読み込み元に一覧に無いファイルがあっても、一覧にあるものだけを入れ、余分は数えるだけ"""
        with tempfile.TemporaryDirectory() as d:
            raw = os.path.join(d, "sources_raw")
            write(os.path.join(raw, "yosan-r8-gaiyou.pdf"), PDF)
            write(os.path.join(raw, "yosan-r8-gaiyou.txt"), b"x")       # 同じ id のほかの拡張子
            write(os.path.join(raw, "kaiken-20260225-page.html"), b"<html>")  # html の行（入れない形式）
            write(os.path.join(raw, "old-id.pdf"), PDF)                # 台帳に無い id
            rows = [{"id": "yosan-r8-gaiyou", "category": "yosan", "url": TOWN + "a.pdf", "format": "pdf",
                     "sha256": hashlib.sha256(PDF).hexdigest()},
                    {"id": "kaiken-20260225-page", "category": "kaiken", "url": "https://h/1.html", "format": "html",
                     "sha256": ""}]
            items = bundle.doc_items(rows, raw)
            present, missing, mismatch = bundle.resolve_items(items)
            self.assertEqual([x["src"] for x in present], [os.path.join(raw, "yosan-r8-gaiyou.pdf")])
            self.assertEqual((missing, mismatch), ([], []))
            extra = bundle.extra_files(raw, {s for it in items for s in it["srcs"]})
            self.assertEqual([os.path.basename(x) for x in extra],
                             ["kaiken-20260225-page.html", "old-id.pdf", "yosan-r8-gaiyou.txt"])
            with tempfile.TemporaryDirectory() as out:
                bundle.copy_items(out, present)
                got = [os.path.relpath(os.path.join(dp, f), out) for dp, _, fs in os.walk(out) for f in fs]
                self.assertEqual(got, [os.path.join(P, "原典", "資料", "yosan", "yosan-r8-gaiyou.pdf")])
            self.assertEqual(bundle.extra_files(os.path.join(d, "nai"), set()), [])


class FetchTest(unittest.TestCase):
    def items(self, d, names):
        return [{"kind": "bulletin", "url": TOWN + n, "srcs": [os.path.join(d, "議会だより", n)], "label": n}
                for n in names]

    def test_skip_existing_wait_and_404(self):
        with tempfile.TemporaryDirectory() as d:
            its = self.items(d, ["a.pdf", "b.pdf", "c.pdf", "d.pdf"])
            write(its[0]["srcs"][0], PDF)
            calls, sleeps = [], []

            def opener(url):
                calls.append(url)
                if url.endswith("b.pdf"):
                    raise urllib.error.HTTPError(url, 404, "nf", {}, None)
                if url.endswith("c.pdf"):
                    return b"<html>error</html>"
                return PDF
            got, failed, rest = bundle.fetch_files(its, opener=opener, sleep=sleeps.append, log=lambda *a: None)
            self.assertEqual(calls, [TOWN + "b.pdf", TOWN + "c.pdf", TOWN + "d.pdf"])  # a は取り直さない
            self.assertEqual(sleeps, [1.0, 1.0])  # 2件目から、1秒ずつ空ける
            self.assertEqual([x["label"] for x in got], ["d.pdf"])
            self.assertEqual([(x["label"], why) for x, why in failed][0], ("b.pdf", "HTTP 404"))
            self.assertIn("形ではありません", failed[1][1])
            self.assertEqual(rest, [])
            self.assertFalse(os.path.exists(its[2]["srcs"][0]))
            with open(its[3]["srcs"][0], "rb") as f:
                self.assertEqual(f.read(), PDF)

    def test_stop_on_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            its = self.items(d, ["a.pdf", "b.pdf", "c.pdf"])
            calls = []

            def opener(url):
                calls.append(url)
                raise urllib.error.HTTPError(url, 403, "forbidden", {}, None)
            got, failed, rest = bundle.fetch_files(its, opener=opener, sleep=lambda s: None, log=lambda *a: None)
            self.assertEqual(len(calls), 1)
            self.assertEqual(failed[0][1], "HTTP 403")
            self.assertEqual([x["label"] for x in rest], ["b.pdf", "c.pdf"])

    def test_council_pdf_named_like_fetch_pdfs(self):
        # 会議録の PDF：読み込み元に <会議ID>_<ファイル名> で置く（scripts/fetch-pdfs.mjs と同じ）。進み具合を出す
        meta = {"meetings": [{"id": "0000001", "pdfs": [{"url": TOWN + "1/4nitime.pdf"}]},
                             {"id": "0000002", "pdfs": [{"url": TOWN + "2/4nitime.pdf"}]}], "toc": []}
        with tempfile.TemporaryDirectory() as d:
            pdf_dir = os.path.join(d, "議事録本体")
            its = bundle.council_items(meta, bundle.COUNCIL_DIR, pdf_dir)
            logs = []
            got, failed, rest = bundle.fetch_files(its, opener=lambda u: PDF, sleep=lambda s: None, log=logs.append)
            self.assertEqual(len(got), 2)
            self.assertEqual(sorted(os.listdir(pdf_dir)), ["0000001_4nitime.pdf", "0000002_4nitime.pdf"])
            self.assertTrue(logs[0].startswith("  [1/2] 取った："))
            self.assertTrue(logs[1].startswith("  [2/2] 取った："))
            present, missing, mismatch = bundle.resolve_items(its)
            self.assertEqual((len(present), missing, mismatch), (2, [], []))

    def test_html_error_page_not_placed(self):
        with tempfile.TemporaryDirectory() as d:
            its = self.items(d, ["a.pdf"])
            got, failed, rest = bundle.fetch_files(its, opener=lambda u: b"<!DOCTYPE html><title>error</title>",
                                                   sleep=lambda s: None, log=lambda *a: None)
            self.assertEqual(got, [])
            self.assertIn("形ではありません", failed[0][1])
            self.assertEqual(os.listdir(d), [])  # フォルダも一時のファイルも作らない

    def test_stop_after_consecutive_failures(self):
        with tempfile.TemporaryDirectory() as d:
            its = self.items(d, [f"{c}.pdf" for c in "abcdefgh"])
            calls = []

            def opener(url):
                calls.append(url)
                if url.endswith("a.pdf"):
                    return PDF
                raise urllib.error.HTTPError(url, 404, "nf", {}, None)
            logs = []
            got, failed, rest = bundle.fetch_files(its, opener=opener, sleep=lambda s: None, log=logs.append)
            self.assertEqual(len(calls), 1 + bundle.FETCH_FAIL_LIMIT)  # a と、続けて失敗した5件
            self.assertEqual(len(failed), 5)
            self.assertEqual([x["label"] for x in rest], ["g.pdf", "h.pdf"])
            self.assertIn("続いたので止めます", logs[-1])

    def test_success_resets_streak(self):
        with tempfile.TemporaryDirectory() as d:
            names = [f"{i:02d}.pdf" for i in range(10)]
            its = self.items(d, names)
            ok = {"04.pdf", "09.pdf"}  # 失敗4件のあと成功、を繰り返す

            def opener(url):
                if url.rsplit("/", 1)[-1] in ok:
                    return PDF
                return b"<html></html>"
            got, failed, rest = bundle.fetch_files(its, opener=opener, sleep=lambda s: None, log=lambda *a: None)
            self.assertEqual((len(got), len(failed), rest), (2, 8, []))

    def test_no_partial_file_when_write_fails(self):
        with tempfile.TemporaryDirectory() as d:
            dst = os.path.join(d, "x", "a.pdf")
            orig = bundle.os.replace

            def bad_replace(a, b):
                raise OSError("disk")
            bundle.os.replace = bad_replace
            try:
                with self.assertRaises(OSError):
                    bundle.write_atomic(dst, PDF)
            finally:
                bundle.os.replace = orig
            self.assertEqual(os.listdir(os.path.join(d, "x")), [])

    def test_user_agent(self):
        seen = {}

        class Res(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            seen["ua"] = req.get_header("User-agent")
            return Res(PDF)
        orig = bundle.urllib.request.urlopen
        bundle.urllib.request.urlopen = fake_urlopen
        try:
            self.assertEqual(bundle.http_get("https://example.org/a.pdf"), PDF)
        finally:
            bundle.urllib.request.urlopen = orig
        self.assertEqual(seen["ua"], bundle.USER_AGENT)
        self.assertIn("hino-portal", seen["ua"])


class NoMarkBundledTest(unittest.TestCase):
    RULE = {"selector": ".tlcap", "note_before": "#sessionTL", "note": "全部", "note_partial": "一部",
            "unless_bundled": "議会だより"}

    def test_states(self):
        self.assertEqual(bundle.no_mark_css([self.RULE], {"議会だより": "all"}), "")
        self.assertIn('content:"一部"', bundle.no_mark_css([self.RULE], {"議会だより": "some"}))
        self.assertIn('content:"全部"', bundle.no_mark_css([self.RULE], {"議会だより": "none"}))
        self.assertIn('content:"全部"', bundle.no_mark_css([self.RULE]))

    def test_lock_rules_have_partial_note(self):
        lock = bundle.load_lock(os.path.join(bundle.REPO_ROOT, "bundle.lock.json"))
        gikai = [r for r in lock["repos"] if r["name"] == "council-dashboard"][0]
        for r in gikai["no_mark"]:
            self.assertEqual(r["unless_bundled"], "議会だより")
            self.assertIn("手元に無い号", r["note_partial"])
            self.assertEqual(bundle.no_mark_css([r], {"議会だより": "all"}), "")


class ListAndReadmeTest(unittest.TestCase):
    ROWS = [{"id": "yosan-r8-gaiyou", "category": "yosan", "title": "令和8年度当初予算の概要", "fiscal_year": "2026",
             "date": "", "url": "u1", "format": "pdf"},
            {"id": "kaiken-20260225-page", "category": "kaiken", "title": "記者会見, 2月", "fiscal_year": "2025",
             "date": "2026-02-25", "url": "u2", "format": "html"},
            {"id": "koho-no790", "category": "koho", "title": "広報ひの", "fiscal_year": "2026", "date": "2026-05",
             "url": "u3", "format": "pdf"}]

    def test_shiryo_list(self):
        present = [{"kind": "doc", "url": "u1", "dest": f"{P}/原典/資料/yosan/yosan-r8-gaiyou.pdf"}]
        names = {"yosan": "予算", "kaiken": "記者会見"}
        text = bundle.shiryo_list_csv(self.ROWS, present, names)
        lines = text.split("\r\n")
        self.assertEqual(lines[0], "番号,分類,タイトル,年度（西暦）,日付,一式の中のファイル,町のホームページの URL")
        self.assertEqual(lines[1], "yosan-r8-gaiyou,予算,令和8年度当初予算の概要,2026,,原典/資料/yosan/yosan-r8-gaiyou.pdf,u1")
        self.assertEqual(lines[2], 'kaiken-20260225-page,記者会見,"記者会見, 2月",2025,2026-02-25,,u2')
        self.assertEqual(lines[3], "koho-no790,koho,広報ひの,2026,2026-05,,u3")  # 名前の無い分類は略のまま

    def test_shiryo_cat_names(self):
        js = ('// x\nwindow.SHIRYO={"inputs":{},"cats":[["keikaku","計画"],["yosan","予算"],["koho","広報ひの"]],'
              '"docs":[{"c":"yosan"}]};').encode()
        names, unknown = bundle.shiryo_cat_names({f"{P}/hino-shiryo/data/index.js": js}, f"{P}/hino-shiryo",
                                                 self.ROWS)
        self.assertEqual(names, {"keikaku": "計画", "yosan": "予算", "koho": "広報ひの"})
        self.assertEqual(unknown, ["kaiken"])
        self.assertEqual(bundle.shiryo_cat_names({}, f"{P}/hino-shiryo", self.ROWS[:1]), ({}, ["yosan"]))

    ITEMS = [{"name": "hino-portal", "title": "ポータル", "commit": "0" * 40, "date": datetime.date(2026, 11, 10),
              "dest": P},
             {"name": "council-dashboard", "title": "議会だより・一般質問", "commit": "1" * 40,
              "date": datetime.date(2026, 11, 10), "dest": f"{P}/council-dashboard"},
             {"name": "hino-council-search", "title": "会議録 横断検索", "commit": "2" * 40,
              "date": datetime.date(2026, 11, 10), "dest": C}]

    def readme(self, counts):
        led = [{"name": "hino-town-docs", "title": "町の資料の一覧と原典", "commit": "3" * 40, "use": "data/sources.tsv",
                "date": datetime.date(2026, 11, 9)}]
        return bundle.readme_text(datetime.date(2026, 11, 11), self.ITEMS, counts, led)

    def test_all(self):
        t = self.readme({"plan": (146, 146), "doc": (1111, 1111), "bulletin": (13, 13), "photo": (14, 14),
                         "council": (269, 269)})
        self.assertIn("計画の原典：146 件のうち、入れたもの 146 件、入れていないもの 0 件", t)
        self.assertIn("会議録：269 件のうち、入れたもの 269 件、入れていないもの 0 件", t)
        self.assertNotIn("原典の PDF を入れていません", t)
        self.assertNotIn("入れていない資料へのリンク", t)
        self.assertIn("council-dashboard/写真/：議員の写真", t)
        self.assertIn("原典/議会だより/：議会だより", t)
        self.assertIn("議事録本体/：会議録の PDF", t)
        self.assertIn("資料の一覧.csv", t)
        self.assertIn("町の資料の一覧と原典\r\n  リポジトリ：hino-town-docs\r\n  版の番号：" + "3" * 40
                      + "\r\n  版の日付：2026年11月9日\r\n  使い方：", t)
        self.assertNotRegex(t, "[—―]|台帳")

    def test_partial(self):
        t = self.readme({"plan": (146, 100), "doc": (1111, 0), "bulletin": (13, 13), "photo": (14, 0),
                         "council": (269, 0)})
        self.assertIn("入れていない資料へのリンクは、町のホームページの URL のままで", t)
        self.assertIn("町の資料：1111 件のうち、入れたもの 0 件、入れていないもの 1111 件", t)
        self.assertNotIn("写真/：議員の写真", t)
        self.assertNotIn("議事録本体/", t)

    def test_none(self):
        t = self.readme({"plan": (146, 0), "doc": (1111, 0), "bulletin": (13, 0), "photo": (14, 0), "council": (269, 0)})
        self.assertIn("原典の PDF を入れていません", t)
        self.assertNotIn("のうち、入れたもの", t)


class LocalRefCheckTest(unittest.TestCase):
    def test_refs(self):
        t = ('<a href="../../原典/計画/a/b.pdf#page=3">x</a>{"t":"a b","u":"../原典/資料/yosan/x.pdf"}'
             '"pdf":"議事録本体/1_a.pdf",\'写真/1.JPG\',"https://x/原典/a.pdf","x原典/a.pdf",'
             '"../../日野町議会_会議録検索/議事録本体/2.pdf"')
        self.assertEqual(bundle.local_file_refs(t), ["../../原典/計画/a/b.pdf#page=3", "../原典/資料/yosan/x.pdf",
                                                     "議事録本体/1_a.pdf", "写真/1.JPG",
                                                     "../../日野町議会_会議録検索/議事録本体/2.pdf"])

    def test_check_finds_missing_pdf_in_data(self):
        with tempfile.TemporaryDirectory() as out:
            write(os.path.join(out, P, "index.html"), b"<html><body>p</body></html>")
            write(os.path.join(out, P, "hino-shiryo", "index.html"),
                  b'<html><body><script src="data/index.js"></script></body></html>')
            write(os.path.join(out, P, "hino-shiryo", "data", "index.js"),
                  'D={"u":"../原典/資料/yosan/a.pdf"},{"u":"../原典/資料/yosan/b.pdf"}'.encode())
            write(os.path.join(out, P, "原典", "資料", "yosan", "a.pdf"), PDF)
            write(os.path.join(out, C, "index.html"), '<a href="議事録本体/1_a.pdf">a</a>'.encode())
            args = argparse.Namespace(lock=os.path.join(bundle.REPO_ROOT, "bundle.lock.json"), no_browser=True,
                                      timeout=1)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                problems, browsed = bundle.check(out, args)
            log = buf.getvalue()
            self.assertFalse(browsed)
            # b.pdf（データの中）と 議事録本体/1_a.pdf（HTML のリンクの検査とこの検査の両方）
            self.assertEqual(problems, 3, log)
            self.assertIn("3 か所を確かめ、開けないもの 2 件", log)
            self.assertIn("../原典/資料/yosan/b.pdf：ファイルが無い", log)


if __name__ == "__main__":
    unittest.main()
