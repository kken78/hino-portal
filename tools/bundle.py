#!/usr/bin/env python3
"""bundle.py — 手元版（DESIGN.md 11章）を作る道具。

インターネットにつながらない環境で使うための一式を、各リポジトリの公開しているフォルダから束ねる。

  1. bundle.lock.json の版（リポジトリごとのコミット）を、手元の取り出しから git archive で読む。
     作業ツリーの状態には左右されない。その版が手元に無ければ、取り出し方を書いて止まる。
  2. 出力先に 日野町データポータル_手元版/ と 日野町議会_会議録検索/ を作る（11.2）。
     hino-council-search は、そのリポジトリのスクリプトで索引データを埋め込んだ1つの HTML を作り、index.html として置く
     （lock の make。hino-council-search-preview は scripts/build-preview.mjs の preview.html、
       hino-council-search-offline は scripts/build.mjs のオフライン配布用の HTML）。
  3. https://kken78.github.io/<リポジトリの名前>/… へのリンクを、束ねた先への相対のリンクにする（11.4）。
     HTML と JavaScript のファイルに当てる。meta と link rel="canonical"・"alternate" の中は変えない（画面のリンクではないため）。
  4. 全ページの上に帯を差し込み、インターネットにつながるときだけ開けるリンクのあとに「（インターネット）」を付ける CSS を足す。
  5. はじめにお読みください.txt と ファイルの一覧.csv を書く。
  6. 渡す前の検査（11.5）：実行ファイル類・マクロ・autorun.inf、手元のリンク切れ、外からの読み込み、
     実ブラウザ（tools/bundle_check.mjs。Playwright）で全ページを file:// で開いたときの外への通信と JavaScript のエラー。
     1つでもあれば終了コード 1。

原典の PDF（11.2 の 原典/、資料の一覧.csv、PDF へのリンクの書き換え）はまだ扱わない。
今は --allow-missing を付けたときだけ、原典を入れずに作る。

使い方：
  python3 tools/bundle.py --out <出力先> --allow-missing [--src <取り出しの置き場所>] [--lock bundle.lock.json]
                          [--date 2026-11-11] [--replace] [--no-browser]
終了コード：0 検査がすべて通った、1 検査で問題があった、2 作れなかった（指定の誤り、版が無いなど）、
            3 実ブラウザの検査をしていない（--no-browser か Playwright が無い）。
Python は標準ライブラリだけを使う。
"""
import argparse
import csv
import datetime
import fnmatch
import hashlib
import html
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import zipfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SELF_NAME = "hino-portal"

PORTAL_DIR = "日野町データポータル_手元版"
COUNCIL_DIR = "日野町議会_会議録検索"
README_NAME = "はじめにお読みください.txt"
FILELIST_NAME = "ファイルの一覧.csv"
PUBLIC_HOST = "kken78.github.io"

# 束ねないファイル（source からのパス）。公開に要らないもの：作る道具、設計の文書、Pages の設定、版の記録、原典の写し。
DEFAULT_EXCLUDE = [
    ".git*", "**/.git*", ".github/**", ".claude/**", ".nojekyll", "**/.nojekyll",
    "CLAUDE.md", "DESIGN.md", "README.md", "*.md", "**/*.md",
    "tools/**", "scripts/**", "test/**", "tests/**", "**/test/**", "**/tests/**",
    "templates/**", "build/**", "sources/**", "node_modules/**",
    "*.py", "**/*.py", "**/__pycache__/**", "*.pyc", "**/*.pyc",
    "inputs.lock.json", "package.json", "package-lock.json",
    "data/watch.json", "data/watch.tsv",
]
# 除外に当たっても残すもの（ライセンスの文と、同梱の部品は配布元のまま入れる）
KEEP = ["LICENSE*", "**/LICENSE*", "vendor/**"]

# 渡す前の検査 (a)：実行ファイル類・マクロ・autorun.inf・圧縮ファイル
FORBIDDEN_EXT = {
    ".exe", ".dll", ".com", ".bat", ".cmd", ".ps1", ".psm1", ".psd1", ".vbs", ".vbe", ".jse", ".wsf", ".wsh",
    ".msi", ".msp", ".scr", ".pif", ".hta", ".cpl", ".jar", ".sh", ".lnk", ".reg", ".inf", ".app", ".dmg",
    ".pkg", ".deb", ".rpm", ".py", ".pyc", ".pl", ".rb", ".so", ".dylib", ".sys", ".ocx", ".scf", ".url",
    ".docm", ".dotm", ".xlsm", ".xltm", ".xlam", ".pptm", ".potm", ".ppam", ".ppsm", ".sldm", ".xlsb",
    ".zip", ".7z", ".rar", ".cab", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".iso", ".img",
}
OOXML_EXT = {".docx", ".xlsx", ".pptx", ".dotx", ".xltx", ".potx", ".ppsx"}
OLE_EXT = {".doc", ".xls", ".ppt", ".dot", ".xlt", ".pot", ".pps"}
OLE_VBA_MARKERS = ("_VBA_PROJECT".encode("utf-16-le"), "VBA".encode("utf-16-le") + b"\x00\x00")

URL_RE = re.compile(r"https?://kken78\.github\.io/([A-Za-z0-9_.-]+)((?:/[^\s\"'<>`\\()]*)?)")
PROTECT_RE = re.compile(
    r"<meta\b[^>]*>|<link\b[^>]*\brel\s*=\s*[\"']?(?:canonical|alternate)\b[^>]*>", re.I)
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
REWRITE_EXT = {".html", ".htm", ".js", ".mjs"}
JST = datetime.timezone(datetime.timedelta(hours=9))

FONT = ('"Hiragino Sans","Hiragino Kaku Gothic ProN","BIZ UDPGothic","Yu Gothic Medium","Yu Gothic",'
        '"Noto Sans CJK JP","Noto Sans JP",Meiryo,system-ui,sans-serif')
# 帯の色と文字の大きさは shared/shell.css のトークン（--portal-foot-bg の紺、--portal-fs-sub の 14px）と同じ値。
# 共通の部品を持たないページ（議会系）でも同じに見えるよう、帯の中でトークンを定義する。
BAND_STYLE = (
    '<style id="temoto-style">'
    ".temoto-band{--portal-fs-sub:14px;--portal-foot-bg:#0C2547;background:var(--portal-foot-bg);color:#fff;"
    "font-family:" + FONT + ";font-size:var(--portal-fs-sub);font-weight:400;line-height:1.6;"
    "letter-spacing:.02em;text-align:left;margin:0;padding:0}"
    ".temoto-band p{max-width:1080px;margin:0 auto;padding:8px 16px;box-sizing:border-box;color:#fff;"
    "font-size:var(--portal-fs-sub);line-height:1.6}"
    'a[href^="http://"]::after,a[href^="https://"]::after,a[href^="//"]::after{content:"（インターネット）"}'
    "</style>"
)


class BundleError(Exception):
    """作れなかったとき（終了コード 2）"""


# ---------------------------------------------------------------- 日付

def jp_date(d):
    return f"{d.year}年{d.month}月{d.day}日"


# ---------------------------------------------------------------- lock

def load_lock(path):
    try:
        with open(path, encoding="utf-8") as f:
            lock = json.load(f)
    except (OSError, ValueError) as e:
        raise BundleError(f"{path} を読めません：{e}")
    repos = lock.get("repos")
    if not isinstance(repos, list) or not repos:
        raise BundleError(f"{path} に repos がありません")
    seen = set()
    for r in repos:
        for k in ("name", "commit", "source", "dest"):
            if not isinstance(r.get(k), str) or not r[k]:
                raise BundleError(f"{path}：{r.get('name', '?')} に {k} がありません")
        if not re.fullmatch(r"[0-9a-f]{40}", r["commit"]):
            raise BundleError(f"{path}：{r['name']} の commit が40桁の16進数ではありません：{r['commit']}")
        if r["name"] in seen:
            raise BundleError(f"{path}：{r['name']} が2回あります")
        seen.add(r["name"])
        top = r["dest"].split("/")[0]
        if top not in (PORTAL_DIR, COUNCIL_DIR):
            raise BundleError(f"{path}：{r['name']} の dest は {PORTAL_DIR}/ か {COUNCIL_DIR}/ の下にしてください")
        if ".." in r["dest"].split("/") or r["dest"].startswith("/"):
            raise BundleError(f"{path}：{r['name']} の dest が正しくありません")
    return lock


def dest_map(repos):
    """リポジトリの名前 → 束ね先のフォルダ（出力先からのパス）"""
    return {r["name"]: r["dest"] for r in repos}


# ---------------------------------------------------------------- git

def find_repo(name, src):
    p = os.path.join(src, name)
    if os.path.isdir(os.path.join(p, ".git")) or os.path.isfile(os.path.join(p, ".git")):
        return p
    if name == SELF_NAME and os.path.exists(os.path.join(REPO_ROOT, ".git")):
        return REPO_ROOT
    raise BundleError(
        f"{name} の取り出しが {p} にありません。--src で置き場所を指定するか、次で取り出してください：\n"
        f"  git clone https://github.com/kken78/{name} {p}")


def git(repo, *args, binary=False):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if r.returncode != 0:
        raise BundleError(f"git {' '.join(args)}（{repo}）が失敗しました：{r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout if binary else r.stdout.decode("utf-8")


def check_commit(repo, name, commit):
    r = subprocess.run(["git", "-C", repo, "cat-file", "-e", commit + "^{commit}"], capture_output=True)
    if r.returncode != 0:
        raise BundleError(
            f"{name} の版 {commit} が手元の取り出し（{repo}）にありません。浅い取り出しで版が足りないときは、次で取ってきてください：\n"
            f"  git -C {repo} fetch --depth 1 origin {commit}")
    ts = int(git(repo, "show", "-s", "--format=%ct", commit).strip())
    return datetime.datetime.fromtimestamp(ts, JST).date()


def read_tree(repo, commit, source):
    """その版の source の下のファイルを {source からのパス: bytes} で返す（作業ツリーは見ない）"""
    args = ["archive", "--format=tar", commit]
    if source not in (".", ""):
        args += ["--", source]
    data = git(repo, *args, binary=True)
    files = {}
    prefix = "" if source in (".", "") else source.rstrip("/") + "/"
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if m.issym() or m.islnk():
                raise BundleError(f"{repo}：{m.name} はリンクです。手元版にはリンクを入れません")
            if not m.isfile():
                continue
            if not m.name.startswith(prefix):
                continue
            rel = m.name[len(prefix):]
            files[rel] = tar.extractfile(m).read()
    if not files:
        raise BundleError(f"{repo} の版 {commit} に {source} がありません")
    return files


def read_extra(repo, commit, paths):
    out = {}
    for p in paths:
        r = subprocess.run(["git", "-C", repo, "show", f"{commit}:{p}"], capture_output=True)
        if r.returncode != 0:
            raise BundleError(f"{repo} の版 {commit} に {p} がありません")
        out[posixpath.basename(p)] = r.stdout
    return out


# ---------------------------------------------------------------- 選ぶ

def _match(path, patterns):
    return any(fnmatch.fnmatchcase(path, p) for p in patterns)


def is_excluded(path, extra_exclude=()):
    if _match(path, KEEP):
        return False
    return _match(path, DEFAULT_EXCLUDE) or _match(path, list(extra_exclude))


def select(files, extra_exclude=()):
    return {p: b for p, b in files.items() if not is_excluded(p, extra_exclude)}


# ---------------------------------------------------------------- リンクの書き換え（11.4）

def resolve_public_url(url, dests):
    """https://kken78.github.io/<名前>/… を、束ねた先のパス（出力先から）と、? と # のあとに分ける。束ねていなければ None"""
    m = URL_RE.fullmatch(url)
    if not m:
        return None
    name, rest = m.group(1), m.group(2) or ""
    if name not in dests:
        return None
    cut = len(rest)
    for ch in "?#":
        i = rest.find(ch)
        if i != -1:
            cut = min(cut, i)
    path, tail = rest[:cut], rest[cut:]
    path = path.lstrip("/")
    if path == "" or path.endswith("/"):
        path += "index.html"
    elif "." not in path.rsplit("/", 1)[-1]:
        path += "/index.html"
    target = posixpath.normpath(posixpath.join(dests[name], urllib.parse.unquote(path)))
    return target, tail


def rel_link(target, base_dir):
    """出力先からのパス target への、base_dir（出力先からのフォルダ）からの相対のリンク"""
    return posixpath.relpath(target, base_dir or ".")


def rewrite_urls(text, base_dir, dests, protect_html=False, log=None):
    """text の中の公開版の URL を、base_dir から束ねた先への相対のリンクにする。
    protect_html のときは meta と link rel=canonical/alternate の中を変えない。"""
    def repl(m):
        url = m.group(0)
        # 文の終わりの句読点などを URL に含めない
        trail = ""
        while url and url[-1] in ".,;:!":
            trail = url[-1] + trail
            url = url[:-1]
        r = resolve_public_url(url, dests)
        if r is None:
            return m.group(0)
        target, tail = r
        if log is not None:
            log.append((url, target))
        return rel_link(target, base_dir) + tail + trail

    if not protect_html:
        return URL_RE.sub(repl, text)
    out, pos = [], 0
    for pm in PROTECT_RE.finditer(text):
        out.append(URL_RE.sub(repl, text[pos:pm.start()]))
        out.append(pm.group(0))
        pos = pm.end()
    out.append(URL_RE.sub(repl, text[pos:]))
    return "".join(out)


# ---------------------------------------------------------------- 帯（11.3）

def band_html(made, page_date):
    return ('<div class="temoto-band" role="note" aria-label="手元版"><p>'
            f"手元版　{jp_date(made)}作成。このページは{jp_date(page_date)}時点の公開版と同じ内容です。"
            "「（インターネット）」の付いたリンクは、インターネットにつながるときだけ開けます。"
            "</p></div>")


HEAD_END_RE = re.compile(r"</head\s*>", re.I)
BODY_RE = re.compile(r"<body\b[^>]*>", re.I)


def inject(text, band):
    """</head> の前に帯と印の CSS を、<body> の直後に帯を入れる"""
    mb = BODY_RE.search(text)
    if not mb:
        raise BundleError("<body> がありません")
    mh = HEAD_END_RE.search(text, 0, mb.start())
    text = text[:mb.end()] + band + text[mb.end():]
    if mh:
        return text[:mh.start()] + BAND_STYLE + text[mh.start():]
    return text[:mb.start()] + BAND_STYLE + text[mb.start():]


# ---------------------------------------------------------------- hino-council-search

COUNCIL_MAKES = {
    # make の名前 → （動かすスクリプト、できるファイル）。できるファイルの None は site.config.json の ui.offline_file
    "hino-council-search-preview": ("scripts/build-preview.mjs", "preview.html"),
    "hino-council-search-offline": ("scripts/build.mjs", None),
}


def make_council(repo, commit, dest, dests, allow_missing, make):
    """hino-council-search のスクリプトで、索引データを埋め込んだ1つの HTML を作る。
    preview（scripts/build-preview.mjs）：PDF のリンクは 議事録本体/ に向く（原典を入れないとき＝--allow-missing では、
      町のホームページの URL のまま）。会議ページのリンクは出さない。
    offline（scripts/build.mjs の dist/<ui.offline_file>）：PDF と会議ページのリンクは町のホームページの URL のまま。
    どちらも、site.config.json の中の公開版の URL は、束ねた先への相対のリンクにしてから渡す
    （build-preview.mjs は http(s) で始まる固定のリンクを外すので、ポータルへの戻りのリンクを残すため）。"""
    script, product = COUNCIL_MAKES[make]
    if not shutil.which("node"):
        raise BundleError("hino-council-search を作るには Node.js（node）が要ります")
    data = git(repo, "archive", "--format=tar", commit, binary=True)
    with tempfile.TemporaryDirectory(prefix="temoto-council-") as tmp:
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for m in tar.getmembers():
                if m.issym() or m.islnk() or m.name.startswith("/") or ".." in m.name.split("/"):
                    raise BundleError(f"hino-council-search：{m.name} を取り出せません")
            try:
                tar.extractall(tmp, filter="data")
            except TypeError:  # filter の無い古い Python
                tar.extractall(tmp)
        conf_path = os.path.join(tmp, "site.config.json")
        with open(conf_path, encoding="utf-8") as f:
            conf = f.read()
        conf = rewrite_urls(conf, dest, dests)
        conf_local = os.path.join(tmp, "site.config.temoto.json")
        with open(conf_local, "w", encoding="utf-8") as f:
            f.write(conf)
        env = dict(os.environ, HINO_SITE_CONFIG=conf_local)
        env.pop("HINO_PDF_DIR", None)
        if allow_missing:
            env["HINO_PDF_ONLINE"] = "1"
        else:
            env.pop("HINO_PDF_ONLINE", None)
        r = subprocess.run(["node", os.path.join(tmp, *script.split("/"))], cwd=tmp, env=env, capture_output=True)
        if r.returncode != 0:
            raise BundleError(f"hino-council-search の {script} が失敗しました：\n"
                              + r.stderr.decode("utf-8", "replace"))
        if product is None:
            product = "dist/" + json.loads(conf).get("ui", {}).get("offline_file", "会議録検索.html")
        with open(os.path.join(tmp, *product.split("/")), "rb") as f:
            return {"index.html": f.read()}


# ---------------------------------------------------------------- 検査 (a)

def forbidden_reason(path, data):
    base = posixpath.basename(path).lower()
    ext = posixpath.splitext(base)[1]
    if base == "autorun.inf":
        return "autorun.inf"
    if ext in FORBIDDEN_EXT:
        return f"入れないファイルの種類（{ext}）"
    head = data[:4]
    if head[:2] == b"MZ":
        return "実行ファイル（MZ）"
    if head == b"\x7fELF":
        return "実行ファイル（ELF）"
    if head in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return "実行ファイル（Mach-O）"
    if data[:2] == b"#!":
        return "スクリプト（#!）"
    if ext in OOXML_EXT or head == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if any(n.lower().endswith("vbaproject.bin") for n in z.namelist()):
                    return "マクロ（vbaProject.bin）"
        except zipfile.BadZipFile:
            pass
        if head == b"PK\x03\x04" and ext not in OOXML_EXT:
            return "圧縮ファイル"
    if ext in OLE_EXT or head == b"\xd0\xcf\x11\xe0":
        if any(mk in data for mk in OLE_VBA_MARKERS):
            return "マクロ（VBA）"
    return None


# ---------------------------------------------------------------- 検査 (b)：手元のリンク切れ、外からの読み込み

CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+?)['\"]?\s*\)|@import\s+['\"]([^'\"]+)['\"]", re.I)
RESOURCE_ATTRS = {
    ("script", "src"), ("img", "src"), ("img", "srcset"), ("source", "src"), ("source", "srcset"),
    ("iframe", "src"), ("frame", "src"), ("embed", "src"), ("object", "data"), ("video", "src"),
    ("video", "poster"), ("audio", "src"), ("track", "src"), ("input", "src"), ("image", "href"),
    ("use", "href"), ("image", "xlink:href"), ("use", "xlink:href"),
}
NAV_ATTRS = {("a", "href"), ("area", "href")}


class RefParser(HTMLParser):
    """HTML の中の参照（リンクと読み込み）を集める。<script> の中の文字は見ない"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []  # (kind, tag, attr, value)  kind は "link" か "load"
        self._style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for name, val in attrs:
            if val is None:
                continue
            if (tag, name) in NAV_ATTRS:
                self.refs.append(("link", tag, name, val))
            elif (tag, name) in RESOURCE_ATTRS:
                if name == "srcset":
                    for part in val.split(","):
                        part = part.strip().split()
                        if part:
                            self.refs.append(("load", tag, name, part[0]))
                else:
                    self.refs.append(("load", tag, name, val))
            elif tag == "link" and name == "href":
                rel = (a.get("rel") or "").lower().split()
                if any(x in rel for x in ("canonical", "alternate")):
                    continue
                self.refs.append(("load", tag, name, val))
            elif name == "style":
                for m in CSS_URL_RE.finditer(val):
                    self.refs.append(("load", tag, "style", m.group(1) or m.group(2)))
        if tag == "style":
            self._style = True

    handle_startendtag = handle_starttag

    def handle_endtag(self, tag):
        if tag == "style":
            self._style = False

    def handle_data(self, data):
        if self._style:
            for m in CSS_URL_RE.finditer(data):
                self.refs.append(("load", "style", "url", m.group(1) or m.group(2)))


def collect_refs(text):
    p = RefParser()
    p.feed(text)
    p.close()
    return p.refs


def is_external(val):
    v = val.strip().lower()
    return v.startswith("http://") or v.startswith("https://") or v.startswith("//")


def check_ref(page, val, exists):
    """page（出力先からのパス）の中の参照 val が手元で開けるか。開けなければ理由、問題なければ None。
    exists(path) は出力先からのパスのファイルがあるか。外のリンクや # だけのものは None"""
    v = val.strip()
    if not v or v.startswith("#") or v.startswith("//") or SCHEME_RE.match(v):
        if v.lower().startswith("file:"):
            return "file: のリンク"
        return None
    path = re.split(r"[?#]", v, maxsplit=1)[0]
    if path == "":
        return None
    if path.startswith("/"):
        return "/ で始まるリンク（手元では開けない）"
    path = urllib.parse.unquote(path)
    target = posixpath.normpath(posixpath.join(posixpath.dirname(page), path))
    if target == ".." or target.startswith("../"):
        return "一式の外を指すリンク"
    if path.endswith("/") or exists(target) == "dir":
        return "フォルダへのリンク（ファイルとして開けない）"
    if not exists(target):
        return "ファイルが無い"
    return None


# ---------------------------------------------------------------- 書き出し

def write_files(out, files):
    for rel, data in files.items():
        p = os.path.join(out, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)


def readme_text(made, items, allow_missing):
    L = []
    L.append("日野町データポータル　手元版")
    L.append("")
    L.append("インターネットにつながらない環境で使うための一式です。")
    L.append("公開版（https://kken78.github.io/hino-portal/）と同じ画面を、手元のファイルだけで見られるようにしたものです。")
    L.append("")
    L.append(f"作成日：{jp_date(made)}")
    L.append("")
    L.append("【使い方】")
    L.append(f"1. このフォルダ（{PORTAL_DIR}）の index.html をブラウザで開いてください。ポータルが開き、各ページへのリンクがあります。")
    L.append(f"2. 会議録 横断検索は、となりのフォルダ（{COUNCIL_DIR}）の index.html です。ポータルのリンクからも開けます。")
    L.append(f"3. 2つのフォルダ（{PORTAL_DIR} と {COUNCIL_DIR}）は、同じ場所に並べて置いてください。"
             "フォルダの名前を変えたり、片方だけを動かしたりすると、互いのリンクが開けなくなります。")
    L.append("4. 「（インターネット）」の付いたリンク（町のホームページ、GitHub など）は、インターネットにつながるときだけ開けます。")
    L.append("5. 各ページの上の帯に、手元版を作った日と、そのページが同じ内容である公開版の日付を書いています。"
             "各ページの資料の時点は、それぞれのページに書いてあります。")
    if allow_missing:
        L.append("6. この一式には、原典の PDF を入れていません。ページの中の PDF へのリンクは、インターネットにつながるときだけ開けます。")
    L.append("")
    L.append("【中身】")
    L.append(f"{PORTAL_DIR}/")
    L.append("  index.html：ポータル")
    for it in items:
        if it["dest"].startswith(PORTAL_DIR + "/"):
            L.append(f"  {it['dest'][len(PORTAL_DIR) + 1:]}/：{it['title']}")
    L.append(f"  {README_NAME}：この文書")
    L.append(f"  {FILELIST_NAME}：一式のすべてのファイルの名前・大きさ（バイト）・SHA-256（{FILELIST_NAME} 自身を除く）")
    for it in items:
        if it["dest"].startswith(COUNCIL_DIR):
            L.append(f"{COUNCIL_DIR}/")
            L.append(f"  index.html：{it['title']}")
    L.append("")
    L.append("【各ページの元にした版】")
    L.append("GitHub の kken78 の各リポジトリの、次の番号の版から作りました（https://github.com/kken78/<リポジトリの名前>/commit/<番号> で見られます）。")
    L.append("")
    for it in items:
        L.append(f"{it['title']}")
        L.append(f"  リポジトリ：{it['name']}")
        L.append(f"  版の番号：{it['commit']}")
        L.append(f"  版の日付：{jp_date(it['date'])}")
        L.append(f"  置き場所：{it['dest']}/")
    L.append("")
    return "\r\n".join(L)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_list_csv(out):
    rows = []
    for top in (PORTAL_DIR, COUNCIL_DIR):
        base = os.path.join(out, top)
        for dp, dns, fns in os.walk(base):
            dns.sort()
            for fn in sorted(fns):
                p = os.path.join(dp, fn)
                rel = os.path.relpath(p, out).replace(os.sep, "/")
                if rel == f"{PORTAL_DIR}/{FILELIST_NAME}":
                    continue
                with open(p, "rb") as f:
                    data = f.read()
                rows.append((rel, len(data), sha256(data)))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(["ファイル", "大きさ（バイト）", "SHA-256"])
    w.writerows(rows)
    return buf.getvalue(), rows


# ---------------------------------------------------------------- 実ブラウザの検査 (c)

def browser_check(out, pages, timeout_s):
    node = shutil.which("node")
    if not node:
        return None, "node がありません"
    script = os.path.join(HERE, "bundle_check.mjs")
    with tempfile.TemporaryDirectory(prefix="temoto-check-") as tmp:
        lst = os.path.join(tmp, "pages.json")
        res = os.path.join(tmp, "result.json")
        with open(lst, "w", encoding="utf-8") as f:
            json.dump({"root": os.path.abspath(out), "pages": pages, "timeout": timeout_s}, f, ensure_ascii=False)
        r = subprocess.run([node, script, lst, res])
        if r.returncode == 2 or not os.path.exists(res):
            return None, "Playwright を読み込めません（PLAYWRIGHT_MODULE を確かめてください）"
        with open(res, encoding="utf-8") as f:
            return json.load(f), None


# ---------------------------------------------------------------- 本体

def build(args):
    lock_path = os.path.abspath(args.lock)
    lock = load_lock(lock_path)
    repos = lock["repos"]
    dests = dest_map(repos)
    src = os.path.abspath(args.src)
    out = os.path.abspath(args.out)

    if not args.allow_missing:
        raise BundleError("原典の PDF を入れる処理はまだありません。原典を入れずに作るときは --allow-missing を付けてください")

    # 出力先はリポジトリの外
    for r in repos:
        try:
            rp = os.path.realpath(find_repo(r["name"], src))
        except BundleError:
            continue
        if os.path.realpath(out) == rp or os.path.realpath(out).startswith(rp + os.sep):
            raise BundleError(f"出力先 {out} が {r['name']} の中にあります。リポジトリの外を指定してください")
    os.makedirs(out, exist_ok=True)
    for top in (PORTAL_DIR, COUNCIL_DIR):
        p = os.path.join(out, top)
        if os.path.exists(p):
            if not args.replace:
                raise BundleError(f"{p} がすでにあります。作り直すときは --replace を付けてください")
            shutil.rmtree(p)

    made = (datetime.date.fromisoformat(args.date) if args.date else datetime.datetime.now(JST).date())

    # 1. 版を確かめて読む
    items, bundle = [], {}  # bundle: 出力先からのパス → bytes
    owner = {}  # 出力先からのパス → リポジトリの名前
    for r in repos:
        repo = find_repo(r["name"], src)
        date = check_commit(repo, r["name"], r["commit"])
        if r.get("make") in COUNCIL_MAKES:
            files = make_council(repo, r["commit"], r["dest"], dests, args.allow_missing, r["make"])
        elif r.get("make"):
            raise BundleError(f"{r['name']}：知らない make の指定です：{r['make']}")
        else:
            files = select(read_tree(repo, r["commit"], r["source"]), r.get("exclude", []))
        files.update(read_extra(repo, r["commit"], r.get("extra", [])))
        for rel, data in files.items():
            p = posixpath.join(r["dest"], rel)
            if p in bundle:
                raise BundleError(f"{p} が {owner[p]} と {r['name']} の両方にあります")
            if data.startswith(b"version https://git-lfs.github.com/spec/"):
                raise BundleError(f"{r['name']}：{rel} は Git LFS の置き換えの印です。LFS のファイルを取り出してから作ってください")
            bundle[p] = data
            owner[p] = r["name"]
        items.append(dict(r, date=date, title=r.get("title", r["name"])))
        print(f"  {r['name']}  {r['commit'][:12]}（{jp_date(date)}）  {len(files)} ファイル")

    # 2. リンクの書き換えと帯
    date_of = {it["name"]: it["date"] for it in items}
    rewritten, leftovers = 0, []
    for p in sorted(bundle):
        ext = posixpath.splitext(p)[1].lower()
        if ext not in REWRITE_EXT:
            continue
        try:
            text = bundle[p].decode("utf-8")
        except UnicodeDecodeError:
            leftovers.append((p, "UTF-8 で読めないので書き換えていない"))
            continue
        repo_dest = dests[owner[p]]
        is_html = ext in (".html", ".htm")
        # HTML はそのファイルの場所から、JavaScript は読み込むページ（公開しているフォルダの直下の index.html）の場所から
        base = posixpath.dirname(p) if is_html else repo_dest
        log = []
        text = rewrite_urls(text, base, dests, protect_html=is_html, log=log)
        rewritten += len(log)
        if is_html:
            try:
                text = inject(text, band_html(made, date_of[owner[p]]))
            except BundleError as e:
                raise BundleError(f"{p}：{e}")
        bundle[p] = text.encode("utf-8")
    print(f"  公開版へのリンクを書き換えた数：{rewritten}")

    # 書き換えなかったファイルの中の公開版の URL（データのファイルなど）
    for p in sorted(bundle):
        ext = posixpath.splitext(p)[1].lower()
        if ext in REWRITE_EXT:
            continue
        if PUBLIC_HOST.encode() in bundle[p]:
            leftovers.append((p, "公開版の URL がある（データのファイルなので書き換えていない）"))

    write_files(out, bundle)

    # 3. はじめにお読みください.txt と ファイルの一覧.csv
    readme = readme_text(made, items, args.allow_missing)
    with open(os.path.join(out, PORTAL_DIR, README_NAME), "wb") as f:
        f.write(b"\xef\xbb\xbf" + readme.encode("utf-8"))
    csv_text, rows = file_list_csv(out)
    with open(os.path.join(out, PORTAL_DIR, FILELIST_NAME), "wb") as f:
        f.write(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))

    # 数字
    print("束ねた結果：")
    total = 0
    for it in items:
        pre = it["dest"] + "/"
        sub = [r for r in rows if r[0].startswith(pre)]
        if it["name"] == SELF_NAME:
            others = [x["dest"] + "/" for x in items if x["name"] != SELF_NAME]
            sub = [r for r in rows if r[0].startswith(pre) and not any(r[0].startswith(o) for o in others)]
        size = sum(r[1] for r in sub)
        print(f"  {it['name']:<26} {len(sub):>5} ファイル  {size:>12,} バイト")
    total = sum(r[1] for r in rows)
    print(f"  全体                       {len(rows):>5} ファイル  {total:>12,} バイト（{FILELIST_NAME} を除く）")

    for p, why in leftovers:
        print(f"  参考：{p}：{why}")

    return check(out, args)


def all_files(out):
    res = []
    for top in (PORTAL_DIR, COUNCIL_DIR):
        for dp, dns, fns in os.walk(os.path.join(out, top)):
            for fn in fns:
                res.append(os.path.relpath(os.path.join(dp, fn), out).replace(os.sep, "/"))
    return sorted(res)


def check(out, args):
    """渡す前の検査（11.5）。問題の数を返す"""
    files = all_files(out)
    fileset = set(files)
    dirs = set()
    for f in files:
        d = posixpath.dirname(f)
        while d:
            dirs.add(d)
            d = posixpath.dirname(d)

    def exists(p):
        if p in fileset:
            return True
        if p in dirs:
            return "dir"
        return False

    problems = 0
    print("渡す前の検査：")

    # (a)
    bad = []
    for f in files:
        with open(os.path.join(out, f), "rb") as fh:
            why = forbidden_reason(f, fh.read())
        if why:
            bad.append((f, why))
    print(f"  (a) 実行ファイル類・マクロ・autorun.inf：{len(bad)} 件")
    for f, why in bad:
        print(f"      - {f}：{why}")
    problems += len(bad)

    # (b) と、外からの読み込み（静的）
    pages = [f for f in files if f.lower().endswith((".html", ".htm"))]
    broken, external = [], []
    for page in pages:
        with open(os.path.join(out, page), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for kind, tag, attr, val in collect_refs(text):
            if is_external(val):
                if kind == "load":
                    external.append((page, f"<{tag} {attr}>", val))
                continue
            why = check_ref(page, val, exists)
            if why:
                broken.append((page, f"<{tag} {attr}>", val, why))
    print(f"  (b) 手元のリンク切れ（HTML のリンクと、読み込む script・css・画像）：{len(broken)} 件（{len(pages)} ページ）")
    for page, where, val, why in broken[:200]:
        print(f"      - {page}：{where} {val}：{why}")
    if len(broken) > 200:
        print(f"      ほか {len(broken) - 200} 件")
    problems += len(broken)
    print(f"      外からの読み込み（HTML に書いてあるもの）：{len(external)} 件")
    for page, where, val in external:
        print(f"      - {page}：{where} {val}")
    problems += len(external)

    # (c)
    if args.no_browser:
        print("  (c) 実ブラウザの検査：していない（--no-browser）")
        return problems, False
    res, err = browser_check(out, pages, args.timeout)
    if res is None:
        print(f"  (c) 実ブラウザの検査：していない（{err}）")
        return problems, False
    req = sum(len(x["requests"]) for x in res)
    jserr = sum(len(x["pageErrors"]) for x in res)
    con = sum(len(x["consoleErrors"]) for x in res)
    miss = sum(len(x["failed"]) for x in res)
    loaderr = [x for x in res if x.get("loadError")]
    print(f"  (c) 実ブラウザ（file://）で開いたページ：{len(res)} / {len(pages)}")
    print(f"      外への通信：{req} 件")
    print(f"      JavaScript のエラー：{jserr} 件")
    print(f"      コンソールのエラー：{con} 件")
    print(f"      手元のファイルを読めなかったもの：{miss} 件")
    print(f"      開けなかったページ：{len(loaderr)} 件")
    for x in res:
        for kind, label in (("requests", "外への通信"), ("pageErrors", "JavaScript のエラー"),
                            ("consoleErrors", "コンソールのエラー"), ("failed", "読めなかったもの")):
            for v in x[kind]:
                print(f"      - {x['page']}：{label}：{v}")
        if x.get("loadError"):
            print(f"      - {x['page']}：開けなかった：{x['loadError']}")
    problems += req + jserr + con + miss + len(loaderr) + (len(pages) - len(res))
    return problems, True


def main(argv=None):
    ap = argparse.ArgumentParser(description="手元版（DESIGN.md 11章）を作る")
    ap.add_argument("--out", required=True, help="出力先（リポジトリの外のフォルダ）")
    ap.add_argument("--src", default=os.path.dirname(REPO_ROOT),
                    help="各リポジトリの取り出しの置き場所（既定は hino-portal の親のフォルダ）")
    ap.add_argument("--lock", default=os.path.join(REPO_ROOT, "bundle.lock.json"), help="版の記録（既定は bundle.lock.json）")
    ap.add_argument("--date", help="作った日（YYYY-MM-DD。既定は今日。日本時間）")
    ap.add_argument("--replace", action="store_true", help="出力先にある前の一式を消して作り直す")
    ap.add_argument("--allow-missing", action="store_true", help="原典の PDF を入れずに作る（原典を入れる処理はまだ無い）")
    ap.add_argument("--no-browser", action="store_true", help="実ブラウザの検査をしない（終了コード 3）")
    ap.add_argument("--check-only", action="store_true", help="束ねずに、出力先の一式の検査だけをする")
    ap.add_argument("--timeout", type=int, default=120, help="実ブラウザで1ページを開くのを待つ秒数（既定 120）")
    args = ap.parse_args(argv)
    try:
        if args.check_only:
            problems, browsed = check(os.path.abspath(args.out), args)
        else:
            problems, browsed = build(args)
    except BundleError as e:
        print(f"止めました：{e}", file=sys.stderr)
        return 2
    if problems:
        print(f"検査で問題が {problems} 件ありました。")
        return 1
    if not browsed:
        print("実ブラウザの検査をしていないので、渡す前の検査は終わっていません。")
        return 3
    print("検査はすべて通りました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
