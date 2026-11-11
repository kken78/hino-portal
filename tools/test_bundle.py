"""tools/bundle.py の試験（標準ライブラリの unittest）。

  python3 -m unittest discover -s tools -p 'test_*.py'
"""
import io
import os
import sys
import tempfile
import unittest
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

    def test_bad_commit(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('{"repos":[{"name":"a","commit":"abc","source":".","dest":"%s/a"}]}' % P)
        try:
            with self.assertRaises(bundle.BundleError):
                bundle.load_lock(f.name)
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
