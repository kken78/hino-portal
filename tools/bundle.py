#!/usr/bin/env python3
"""bundle.py — 手元版（DESIGN.md 11章）を作る道具。

インターネットにつながらない環境で使うための一式を、各リポジトリの公開しているフォルダから束ねる。

  1. bundle.lock.json の版（リポジトリごとのコミット）を、手元の取り出しから git archive で読む。
     作業ツリーの状態には左右されない。その版が手元に無ければ、取り出し方を書いて止まる。
  2. 出力先に 日野町データポータル_手元版/ と 日野町議会_会議録検索/ を作る（11.2）。
     hino-council-search は、そのリポジトリのスクリプトで索引データを埋め込んだ1つの HTML を作り、index.html として置く
     （lock の make: hino-council-search-offline。scripts/build.mjs が作る配布用の HTML）。
  3. https://kken78.github.io/<リポジトリの名前>/… へのリンクを、束ねた先への相対のリンクにする（11.4）。
     HTML と JavaScript のファイルに当てる。meta と link rel="canonical"・"alternate" の中は変えない（画面のリンクではないため）。
  4. 全ページの上に帯を差し込み、インターネットにつながるときだけ開けるリンクのあとに「（インターネット）」を付ける CSS を足す。
  5. 原典を一式に入れる（11.2）。手元にあるものだけを写し、その URL へのリンクを手元のファイルへの相対のリンクにする（11.4）。
       計画の原典   shiga-hino-plans の data/sources_index.tsv（lock の版）の file のある行。
                    読み込み元 <plans-raw>/<id>/<file> → 原典/計画/<id>/<file>。写すときに sha256 を比べる
       町の資料     hino-town-docs の data/sources.tsv（lock の ledgers の版）の format が pdf・xlsx の行。
                    読み込み元 <docs-raw>/<id>.<format> → 原典/資料/<category>/<id>.<format>。写すときに sha256 を比べる
       会議録       hino-council-search の meetings.json・toc.json の PDF（council_pdf_map）。
                    読み込み元 <council-pdf>/<会議ID>_<ファイル名>（scripts/fetch-pdfs.mjs の置き方）→ 日野町議会_会議録検索/議事録本体/
       議会だより   council-dashboard の data/issue-*.json の links.bulletin_pdf（lock の版）。
                    置き場所 <town-files>/議会だより/<ファイル名> → 原典/議会だより/<ファイル名>
       議員の写真   council-dashboard の config.json の members[].photo（lock の版）。
                    置き場所 <town-files>/写真/<ファイル名> → council-dashboard/写真/<ファイル名>
     会議録の PDF と議会だより・議員の写真は、--fetch を付けると、読み込み元・置き場所に無いものを町のホームページから取る
     （1秒に1件、User-Agent を名乗る。PDF などの形でない応答は置かない。失敗が続けて5件あれば止める）。
     URL の一致は、台帳などの URL（町の資料は archive_url も）との完全な一致で見る（# のあとは保つ。? のあとが付いたもの、
     ほかの URL の中にあるものは変えない）。
     手元に無いものがあれば、--allow-missing を付けないかぎり、件数と例を出して止まる。
     sha256 が合わないものは入れず、--on-mismatch skip でなければ止まる。
  6. はじめにお読みください.txt、資料の一覧.csv、ファイルの一覧.csv を書く。
  7. 渡す前の検査（11.5）：実行ファイル類・マクロ・autorun.inf、手元のリンク切れ（ページとデータの中の、原典などへの
     相対のリンクを含む）、外からの読み込み、
     実ブラウザ（tools/bundle_check.mjs。Playwright）で全ページを file:// で開き、タブと # の画面（ページの中の場所へ
     移るだけの # は除く）もたどったときの
     外への通信と JavaScript のエラー、印で字が切れるリンク、幅 360px での帯の行数。
     1つでもあれば終了コード 1。

使い方：
  python3 tools/bundle.py --out <出力先> [--src <取り出しの置き場所>] [--lock bundle.lock.json]
                          [--docs-raw <dir>] [--plans-raw <dir>] [--council-pdf <dir>] [--town-files <dir>] [--fetch]
                          [--allow-missing] [--on-mismatch stop|skip]
                          [--date 2026-11-11] [--replace] [--no-browser]
終了コード：0 検査がすべて通った、1 検査で問題があった、2 作れなかった（指定の誤り、版が無い、原典が無いなど）、
            3 実ブラウザの検査をしていない（--no-browser か Playwright が無い）。
Python は標準ライブラリだけを使う。
"""
import argparse
import contextlib
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
import time
import urllib.error
import urllib.parse
import urllib.request
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


BAND_MAX_LINES = 2  # 幅 360px での帯の行数の上限


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
    ledgers = lock.setdefault("ledgers", [])
    if not isinstance(ledgers, list):
        raise BundleError(f"{path} の ledgers が一覧ではありません")
    for r in ledgers:
        for k in ("name", "commit", "use"):
            if not isinstance(r.get(k), str) or not r[k]:
                raise BundleError(f"{path}：ledgers の {r.get('name', '?')} に {k} がありません")
        if not re.fullmatch(r"[0-9a-f]{40}", r["commit"]):
            raise BundleError(f"{path}：ledgers の {r['name']} の commit が40桁の16進数ではありません：{r['commit']}")
        if r["name"] in seen:
            raise BundleError(f"{path}：{r['name']} が2回あります")
        if "dest" in r or "source" in r:
            raise BundleError(f"{path}：ledgers の {r['name']} は画面を束ねないので、dest と source を書きません")
        seen.add(r["name"])
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
            f"手元版（{jp_date(made)}作成）　公開版の{jp_date(page_date)}時点と同じ内容です。"
            "</p></div>")


def css_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def no_mark_css(rules, bundled=None):
    """lock の no_mark から、印を出さない部品と、その代わりに1回だけ書く文の CSS を作る。
    rules：[{"selector": 印を出さないリンク, "note_before": 文を前に置く要素, "note": 文,
             "note_style": 文の色などをまわりの説明の文に合わせる CSS の宣言（任意）}]。
    幅の決まった部品（札など）の中のリンクは、印を足すと字が切れたり別の行に出たりするため。
    文を置く要素がグリッドのときも1行を占めるように grid-column を付ける。
    unless_bundled（任意）は原典の種類の名前（例「議会だより」）。bundled[その名前] が "all"（すべて一式に入れた）なら
    その規則を使わない（リンクが手元を指すので印も文も要らない）。"some"（一部だけ入れた）なら note の代わりに
    note_partial を使う。"none" か bundled が無いときは、そのまま使う。"""
    css = []
    bundled = bundled or {}
    for r in rules:
        state = bundled.get(r.get("unless_bundled")) if r.get("unless_bundled") else None
        if state == "all":
            continue
        if state == "some" and r.get("note_partial"):
            r = dict(r, note=r["note_partial"])
        sel = r["selector"]
        if not re.fullmatch(r"[A-Za-z0-9_.#\-\[\]=\"' >:,()^$*]+", sel):
            raise BundleError(f"no_mark の selector が正しくありません：{sel}")
        css.append(",".join(f"{x.strip()}::after" for x in sel.split(",")) + "{content:none!important}")
        if r.get("note_before"):
            nb = r["note_before"]
            if not re.fullmatch(r"[A-Za-z0-9_.#\-]+", nb):
                raise BundleError(f"no_mark の note_before が正しくありません：{nb}")
            style = r.get("note_style", "")
            if not re.fullmatch(r"[A-Za-z0-9_.#\-:;,()% ]*", style):
                raise BundleError(f"no_mark の note_style が正しくありません：{style}")
            css.append(f"{nb}::before{{content:{css_string(r['note'])};display:block;grid-column:1/-1;"
                       "font-size:var(--portal-fs-sub,14px);font-weight:400;line-height:1.6;margin:0 0 8px;"
                       + style + "}")
    return "".join(css)


HEAD_END_RE = re.compile(r"</head\s*>", re.I)
BODY_RE = re.compile(r"<body\b[^>]*>", re.I)


def inject(text, band, extra_css=""):
    """</head> の前に帯と印の CSS を、<body> の直後に帯を入れる"""
    mb = BODY_RE.search(text)
    if not mb:
        raise BundleError("<body> がありません")
    mh = HEAD_END_RE.search(text, 0, mb.start())
    text = text[:mb.end()] + band + text[mb.end():]
    style = BAND_STYLE.replace("</style>", extra_css + "</style>") if extra_css else BAND_STYLE
    if mh:
        return text[:mh.start()] + style + text[mh.start():]
    return text[:mb.start()] + style + text[mb.start():]


# ---------------------------------------------------------------- hino-council-search

COUNCIL_MAKES = ("hino-council-search-offline",)
COUNCIL_PDF_DIR = "議事録本体"


def make_council(repo, commit):
    """hino-council-search の scripts/build.mjs で、配布用の HTML（索引データを埋め込んだ1つの HTML。
    dist/<site.config.json の ui.offline_file>）を作る。画面はそのリポジトリが配布用に作るものと同じで、
    公開版へのリンクは、ほかのページと同じく束ねたあとの書き換えで相対のリンクにする。
    PDF と会議ページのリンクは町のホームページの URL のまま（手元にある PDF は、build の原典の処理で council_pdf_map により書き換える）。
    返すもの：({"index.html": bytes}, {"meetings": [...], "toc": [...]})"""
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
        # 手元の環境変数で作り方が変わらないようにする（PDF の同梱と別の設定のファイルを使わない）
        env = {k: v for k, v in os.environ.items() if not k.startswith("HINO_")}
        r = subprocess.run(["node", os.path.join(tmp, "scripts", "build.mjs")], cwd=tmp, env=env, capture_output=True)
        if r.returncode != 0:
            raise BundleError("hino-council-search の scripts/build.mjs が失敗しました：\n"
                              + r.stderr.decode("utf-8", "replace"))
        with open(os.path.join(tmp, "site.config.json"), encoding="utf-8") as f:
            offline = json.load(f).get("ui", {}).get("offline_file", "会議録検索.html")
        with open(os.path.join(tmp, "dist", offline), "rb") as f:
            page = f.read()
        meta = {}
        for k in ("meetings", "toc"):
            with open(os.path.join(tmp, "public", "data", k + ".json"), encoding="utf-8") as f:
                meta[k] = json.load(f)
        return {"index.html": page}, meta


def council_pdf_map(meetings, toc, pdf_dir=COUNCIL_PDF_DIR):
    """会議録の PDF の URL → 手元のパス（<pdf_dir>/<会議ID>_<ファイル名>）。
    hino-council-search の scripts/fetch-pdfs.mjs・build-preview.mjs と同じ名前の付け方
    （ファイル名だけでは会議をまたいで重なるので、会議ID を前に付ける）。
    手元にある PDF だけを、この対応で一式に写し、index.html の中の URL を書き換える（build の原典の処理）。"""
    out = {}
    for group in (meetings, toc):
        for m in group:
            for p in m.get("pdfs") or []:
                u = p.get("url")
                if u and "://" in u:
                    out.setdefault(u, f"{pdf_dir}/{m['id']}_{u.rsplit('/', 1)[-1]}")
    return out


# ---------------------------------------------------------------- 原典（11.2・11.4）

GENTEN_DIR = "原典"
PLAN_DIR = f"{GENTEN_DIR}/計画"
DOCS_DIR = f"{GENTEN_DIR}/資料"
BULLETIN_DIR = f"{GENTEN_DIR}/議会だより"
PHOTO_DIR = "写真"  # council-dashboard の束ね先の中
SHIRYO_LIST_NAME = "資料の一覧.csv"
DOCS_REPO = "hino-town-docs"
PLANS_REPO = "shiga-hino-plans"
COUNCIL_REPO = "hino-council-search"
GIKAI_REPO = "council-dashboard"
PLANS_LEDGER = "data/sources_index.tsv"
DOCS_LEDGER = "data/sources.tsv"
DOCS_FORMATS = ("pdf", "xlsx")  # html の行は町のホームページの本文で、原典のファイルではないので入れない
USER_AGENT = "hino-portal-bundle (+https://github.com/kken78/hino-portal)"
FETCH_INTERVAL = 1.0  # 町のホームページから取るときの間（秒）
FETCH_FAIL_LIMIT = 5  # 失敗がこの件数続いたら、残りを取りに行かずに止める
# 種類（はじめにお読みください.txt と数字の順）
KINDS = [("plan", "計画の原典"), ("doc", "町の資料"), ("bulletin", "議会だより"), ("photo", "議員の写真"),
         ("council", "会議録")]
KIND_NAME = dict(KINDS)
MAGIC = {".pdf": b"%PDF-", ".jpg": b"\xff\xd8\xff", ".jpeg": b"\xff\xd8\xff", ".png": b"\x89PNG"}
LOCAL_DIRS = (GENTEN_DIR, COUNCIL_PDF_DIR, PHOTO_DIR)  # 検査で、書き換えたリンクとみなすフォルダの名前
SAFE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._()\-]*")


def read_ledger(text, need, where):
    """TSV（1行目が見出し。引用符を使わない）を読む。need の列が無ければ止める"""
    rd = csv.DictReader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    missing = [c for c in need if c not in (rd.fieldnames or [])]
    if missing:
        raise BundleError(f"{where} に列 {'・'.join(missing)} がありません")
    return list(rd)


def _safe(name, where):
    if not SAFE_NAME_RE.fullmatch(name) or ".." in name:
        raise BundleError(f"{where}：ファイル名に使えない字があります：{name}")
    return name


def url_ext(url):
    """URL の拡張子（hino-town-docs の tools/htd.py の ext_of と同じ見方。? のあとは見ない）"""
    return os.path.splitext(url.split("?")[0])[1].lower().lstrip(".")


def plan_items(rows, raw_dir):
    """計画の原典：file のある行。sources_raw/<id>/<file> → 原典/計画/<id>/<file>"""
    out = []
    for r in rows:
        if not r.get("file"):
            continue
        where = f"{PLANS_REPO}/{PLANS_LEDGER} の {r['id']}"
        pid, fn = _safe(r["id"], where), _safe(r["file"], where)
        out.append({"kind": "plan", "url": r["url"], "srcs": [os.path.join(raw_dir, pid, fn)],
                    "dest": f"{PORTAL_DIR}/{PLAN_DIR}/{pid}/{fn}", "sha256": (r.get("sha256") or "").lower(),
                    "label": f"{pid}/{fn}"})
    return out


def doc_items(rows, raw_dir):
    """町の資料：format が pdf・xlsx の行。sources_raw/<id>.<拡張子> → 原典/資料/<category>/<id>.<format>。
    archive_url のある行は、その URL も同じファイルの URL とする（aliases）"""
    out = []
    for r in rows:
        fmt = (r.get("format") or "").lower()
        if fmt not in DOCS_FORMATS:
            continue
        where = f"{DOCS_REPO}/{DOCS_LEDGER} の {r['id']}"
        i, cat = _safe(r["id"], where), _safe(r["category"], where)
        exts = [fmt] + ([url_ext(r["url"])] if url_ext(r["url"]) not in ("", fmt) else [])
        # 保存版の URL（台帳の archive_url）は、同じファイルを指す別の URL として、完全に一致するものだけを書き換える
        alias = [r["archive_url"]] if r.get("archive_url") else []
        out.append({"kind": "doc", "url": r["url"], "srcs": [os.path.join(raw_dir, f"{i}.{e}") for e in exts],
                    "dest": f"{PORTAL_DIR}/{DOCS_DIR}/{cat}/{i}.{fmt}", "sha256": (r.get("sha256") or "").lower(),
                    "label": i, "aliases": alias})
    return out


def council_items(meta, council_dest, pdf_dir):
    """会議録：council_pdf_map の対応。<pdf_dir>/<会議ID>_<ファイル名> → <council_dest>/議事録本体/…"""
    out = []
    for url, rel in council_pdf_map(meta["meetings"], meta["toc"]).items():
        name = _safe(rel.split("/", 1)[1], f"{COUNCIL_REPO} の会議録の PDF")
        out.append({"kind": "council", "url": url, "srcs": [os.path.join(pdf_dir, name)],
                    "dest": f"{council_dest}/{COUNCIL_PDF_DIR}/{name}", "sha256": "", "label": name})
    return out


def url_basename(url):
    return urllib.parse.unquote(re.split(r"[?#]", url, maxsplit=1)[0].rsplit("/", 1)[-1])


def gikai_town_urls(repo, commit):
    """council-dashboard の lock の版から、議会だよりの PDF（data/issue-*.json の links.bulletin_pdf）と
    議員の写真（config.json の members[].photo）の URL を、出てくる順に重ねずに返す"""
    def uniq(xs):
        seen, res = set(), []
        for x in xs:
            if x and x not in seen:
                seen.add(x)
                res.append(x)
        return res
    try:
        config = json.loads(git(repo, "show", f"{commit}:config.json"))
    except ValueError as e:
        raise BundleError(f"{GIKAI_REPO} の config.json を読めません：{e}")
    photos = uniq(m.get("photo", "") for m in config.get("members", []))
    names = git(repo, "ls-tree", "--name-only", commit, "data/").split()
    issues = sorted((n for n in names if re.fullmatch(r"data/issue-\d+\.json", n)),
                    key=lambda n: int(re.search(r"\d+", n).group(0)))
    bulletins = []
    for n in issues:
        try:
            j = json.loads(git(repo, "show", f"{commit}:{n}"))
        except ValueError as e:
            raise BundleError(f"{GIKAI_REPO} の {n} を読めません：{e}")
        bulletins.append((j.get("links") or {}).get("bulletin_pdf", ""))
    return uniq(bulletins), photos


def town_file_items(bulletins, photos, gikai_dest, town_dir):
    """議会だよりと議員の写真。置き場所 <town_dir>/議会だより/・写真/ に、URL のファイル名で置く"""
    out = []
    for kind, urls, sub, dest_dir in (("bulletin", bulletins, "議会だより", f"{PORTAL_DIR}/{BULLETIN_DIR}"),
                                      ("photo", photos, PHOTO_DIR, f"{gikai_dest}/{PHOTO_DIR}")):
        for u in urls:
            if not re.match(r"https?://", u):
                continue
            name = _safe(url_basename(u), f"{GIKAI_REPO} の{KIND_NAME[kind]}の URL {u}")
            out.append({"kind": kind, "url": u, "srcs": [os.path.join(town_dir, sub, name)],
                        "dest": f"{dest_dir}/{name}", "sha256": "", "label": name})
    return out


def check_items(items):
    """同じ束ね先に2つ以上を写さないこと"""
    seen = {}
    for it in items:
        if it["dest"] in seen:
            raise BundleError(f"{it['dest']} に {seen[it['dest']]} と {it['url']} の2つを写すことになります")
        seen[it["dest"]] = it["url"]


def magic_problem(name, data):
    """拡張子に合わない中身なら理由を返す（町のホームページのエラーのページを PDF として置かないため）"""
    head = MAGIC.get(posixpath.splitext(name.lower())[1])
    if head and not data.startswith(head):
        return f"中身が {posixpath.splitext(name)[1]} の形ではありません"
    if not data:
        return "大きさが 0 です"
    return None


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def write_atomic(dst, data):
    """一時の名前（<dst>.part）で書いてから名前を変える。途中で失敗したら一時のファイルを消す"""
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dst)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


def fetch_files(items, opener=http_get, sleep=time.sleep, log=print, fail_limit=FETCH_FAIL_LIMIT):
    """読み込み元・置き場所（item の srcs）に無いものを町のホームページから取り、srcs[0] に置く。
    会議録の PDF、議会だより、議員の写真に使う。1秒に1件。すでにあるものは取り直さない。
    中身が拡張子の形でないもの（HTML のエラーのページなど）は置かずに失敗とする。
    404 と中身の形の誤りは記録して続ける。それ以外の失敗（断られた、つながらない）か、
    失敗が fail_limit 件続いたときは、そこで止める（残りは取らない）。
    返すもの：(取った, [(item, 理由)], 取らなかった)"""
    todo = [it for it in items if not any(os.path.isfile(s) for s in it["srcs"])]
    got, failed, rest = [], [], []
    streak = 0
    for n, it in enumerate(todo):
        if n:
            sleep(FETCH_INTERVAL)
        head = f"  [{n + 1}/{len(todo)}]"
        stop = False
        try:
            data = opener(it["url"])
        except urllib.error.HTTPError as e:
            why, stop = f"HTTP {e.code}", e.code != 404
        except Exception as e:  # つながらない・時間切れなど
            why, stop = (str(e).splitlines()[0] if str(e) else type(e).__name__), True
        else:
            why = magic_problem(it["srcs"][0], data)
        if why:
            failed.append((it, why))
            streak += 1
            log(f"{head} 取れなかった：{it['url']}：{why}")
            if stop or streak >= fail_limit:
                rest = todo[n + 1:]
                if not stop:
                    log(f"  失敗が {streak} 件続いたので止めます。")
                break
            continue
        streak = 0
        write_atomic(it["srcs"][0], data)
        got.append(it)
        log(f"{head} 取った：{it['url']}")
    return got, failed, rest


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extra_files(root, used):
    """読み込み元 root の下にあって、一覧のどれにも当たらないファイル（写さない。件数を出すだけ）"""
    used = {os.path.abspath(u) for u in used}
    out = []
    if not os.path.isdir(root):
        return out
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for fn in sorted(fns):
            p = os.path.abspath(os.path.join(dp, fn))
            if p not in used:
                out.append(p)
    return out


def resolve_items(items):
    """手元にあるか、sha256（台帳にあるもの）か中身の形が合うかを見る。
    返すもの：(入れるもの, 無いもの, [(合わないもの, 理由)])。入れるものには src を足す"""
    present, missing, mismatch = [], [], []
    for it in items:
        src = next((s for s in it["srcs"] if os.path.isfile(s)), None)
        if src is None:
            missing.append(it)
            continue
        if it["sha256"]:
            got = file_sha256(src)
            if got != it["sha256"]:
                mismatch.append((dict(it, src=src), f"sha256 が台帳と違う（手元 {got[:12]}…、台帳 {it['sha256'][:12]}…）"))
                continue
        else:
            with open(src, "rb") as f:
                why = magic_problem(src, f.read(16))
            if why:
                mismatch.append((dict(it, src=src), why))
                continue
        present.append(dict(it, src=src))
    return present, missing, mismatch


def file_map(present):
    """URL → 束ね先のパス。同じ URL が2つ以上あるときは KINDS の順で先のもの（計画の原典と町の資料の両方にある資料は
    計画の原典を、台帳の中で同じ URL が2行あるときは先の行を指す）"""
    order = {k: n for n, (k, _) in enumerate(KINDS)}
    out = {}
    for it in sorted(present, key=lambda x: order[x["kind"]]):
        out.setdefault(it["url"], it["dest"])
    for it in sorted(present, key=lambda x: order[x["kind"]]):
        for a in it.get("aliases", []):
            out.setdefault(a, it["dest"])
    return out


# URL の候補は、URL に使える ASCII の字の続き（全角のかっこや句読点、引用符で切れる）
TOWN_URL_RE = re.compile(r"(?<![\w/.\-=%:@])https?://[A-Za-z0-9\-._~:/?#\[\]@!$&()*+,;=%]+")
URL_TRAIL = ".,;:!)"


def href_path(p):
    """相対のリンクの中で意味の変わる字だけを % にする（日本語の字はそのまま。ほかの書き換えと同じ）"""
    return re.sub(r"[%#?\s\"'<>\\`]", lambda m: urllib.parse.quote(m.group(0), safe=""), p)


def _outside_protected(text, func, protect_html):
    if not protect_html:
        return func(text)
    out, pos = [], 0
    for pm in PROTECT_RE.finditer(text):
        out.append(func(text[pos:pm.start()]))
        out.append(pm.group(0))
        pos = pm.end()
    out.append(func(text[pos:]))
    return "".join(out)


def rewrite_local_files(text, base_dir, fmap, known=(), protect_html=False, log=None, online=None):
    """text の中の URL のうち、fmap（一式に入れたファイルの URL → 束ね先）にあるものを、base_dir からの相対のリンクにする。
    URL の一致は完全な一致で見る（# のあとは保つ。? のあとが付いたもの、ほかの URL の中にあるものは変えない）。
    known（一式に入れられたはずの URL）にあって fmap に無いものは、そのままにし、online に足す。"""
    def repl(m):
        s, trail = m.group(0), ""
        while s:
            url, sep, frag = s.partition("#")
            if url in fmap:
                if log is not None:
                    log.append((url, fmap[url]))
                return href_path(rel_link(fmap[url], base_dir)) + sep + frag + trail
            if url in known:
                if online is not None:
                    online.append(url)
                return m.group(0)
            if s[-1] in URL_TRAIL:
                trail = s[-1] + trail
                s = s[:-1]
                continue
            break
        return m.group(0)
    return _outside_protected(text, lambda t: TOWN_URL_RE.sub(repl, t), protect_html)


def copy_items(out, present):
    for it in present:
        dst = os.path.join(out, *it["dest"].split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(it["src"], dst)


def summary_counts(items, present):
    """種類ごとの (全部, 入れた)"""
    res = {}
    for k, _ in KINDS:
        res[k] = (sum(1 for x in items if x["kind"] == k), sum(1 for x in present if x["kind"] == k))
    return res


def bundled_state(counts):
    """no_mark の unless_bundled に渡す、種類の名前 → all・some・none"""
    res = {}
    for k, name in KINDS:
        total, got = counts.get(k, (0, 0))
        res[name] = "all" if total and got == total else ("some" if got else "none")
    return res


SHIRYO_CATS_RE = re.compile(r'"cats"\s*:\s*(\[\s*\[.*?\]\s*\])', re.S)


def shiryo_cat_names(bundle, shiryo_dest, rows):
    """町の資料の検索（hino-shiryo）の画面が使う分類の名前（束ねた data/index.js の cats。hino-shiryo の
    tools/build_data.py の CATS と同じもの）を読む。返すもの：({略: 名前}, [名前の無い略])"""
    names = {}
    data = bundle.get(f"{shiryo_dest}/data/index.js") if shiryo_dest else None
    if data:
        m = SHIRYO_CATS_RE.search(data.decode("utf-8", "replace"))
        if m:
            try:
                names = {c: n for c, n in json.loads(m.group(1))}
            except (ValueError, TypeError):
                names = {}
    unknown = sorted({r["category"] for r in rows if r["category"] not in names})
    return names, unknown


def shiryo_list_csv(rows, present, cat_names=None):
    """資料の一覧.csv：町の資料の台帳の全行。分類は町の資料の検索の画面の名前（無いものは略のまま）。
    一式の中のファイルは、入れたものだけ書く"""
    cat_names = cat_names or {}
    where = {it["url"]: it["dest"] for it in present if it["kind"] == "doc"}
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(["番号", "分類", "タイトル", "年度（西暦）", "日付", "一式の中のファイル", "町のホームページの URL"])
    for r in rows:
        dest = where.get(r["url"], "")
        if dest.startswith(PORTAL_DIR + "/"):
            dest = dest[len(PORTAL_DIR) + 1:]
        w.writerow([r["id"], cat_names.get(r["category"], r["category"]), r["title"], r.get("fiscal_year", ""), r.get("date", ""), dest, r["url"]])
    return buf.getvalue()


def print_items(title, pairs, limit=10):
    """[(item, 理由)] を種類ごとの件数と例で出す"""
    print(title)
    for k, name in KINDS:
        sub = [(it, why) for it, why in pairs if it["kind"] == k]
        if not sub:
            continue
        print(f"    {name}：{len(sub)} 件")
        for it, why in sub[:limit]:
            print(f"      - {it['label']}（{it['srcs'][0] if 'src' not in it else it['src']}）" + (f"：{why}" if why else ""))
        if len(sub) > limit:
            print(f"      ほか {len(sub) - limit} 件")


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


def readme_text(made, items, counts, ledgers=()):
    """counts：種類ごとの (全部, 入れた)。ledgers：画面を束ねず一覧だけを読むリポジトリ（lock の ledgers に date を足したもの）"""
    gikai = next((it["dest"][len(PORTAL_DIR) + 1:] for it in items if it["name"] == GIKAI_REPO), GIKAI_REPO)
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
    total = sum(t for t, _ in counts.values())
    got = sum(g for _, g in counts.values())
    if got == 0:
        L.append("6. この一式には、原典の PDF を入れていません。ページの中の PDF へのリンクは、インターネットにつながるときだけ開けます。")
    else:
        L.append("6. 原典の PDF など（町の資料の Excel のファイルと、議員の写真を含む）を一式に入れています。置き場所は【中身】のとおりです。"
                 "ページの中のリンクのうち、入れた資料へのリンクは、手元のファイルを開きます。")
        if got < total:
            L.append("   入れていない資料へのリンクは、町のホームページの URL のままで、インターネットにつながるときだけ開けます。")
        L.append("   入れた数と入れていない数は次のとおりです。")
        for k, name in KINDS:
            t, g = counts.get(k, (0, 0))
            if t:
                L.append(f"   {name}：{t} 件のうち、入れたもの {g} 件、入れていないもの {t - g} 件")
        L.append("7. 原典、議会だより、会議録、議員の写真は、町のホームページで公開されているファイルを、そのまま入れたものです。"
                 "各リポジトリのライセンスの対象外で、著作権は日野町、日野町議会などの各発行者にあります。")
    L.append("")
    L.append("【中身】")
    L.append(f"{PORTAL_DIR}/")
    L.append("  index.html：ポータル")
    for it in items:
        if it["dest"].startswith(PORTAL_DIR + "/"):
            L.append(f"  {it['dest'][len(PORTAL_DIR) + 1:]}/：{it['title']}")
            if it["name"] == GIKAI_REPO and counts.get("photo", (0, 0))[1]:
                L.append(f"  {gikai}/{PHOTO_DIR}/：議員の写真")
    if counts.get("plan", (0, 0))[1]:
        L.append(f"  {PLAN_DIR}/<計画の番号>/：計画の原典")
    if counts.get("doc", (0, 0))[1]:
        L.append(f"  {DOCS_DIR}/<分類>/<番号>.pdf など：町の資料（分類と番号は {SHIRYO_LIST_NAME} のとおり）")
    if counts.get("bulletin", (0, 0))[1]:
        L.append(f"  {BULLETIN_DIR}/：議会だより")
    L.append(f"  {README_NAME}：この文書")
    if counts.get("doc", (0, 0))[0]:
        L.append(f"  {SHIRYO_LIST_NAME}：町の資料の一覧（番号・分類・タイトル・年度・日付・一式の中のファイル・町のホームページの URL）。"
                 "一式の中のファイルの欄は、入れたものだけに書いています")
    L.append(f"  {FILELIST_NAME}：一式のすべてのファイルの名前・大きさ（バイト）・SHA-256（{FILELIST_NAME} 自身を除く）")
    for it in items:
        if it["dest"].startswith(COUNCIL_DIR):
            L.append(f"{COUNCIL_DIR}/")
            L.append(f"  index.html：{it['title']}")
            if counts.get("council", (0, 0))[1]:
                L.append(f"  {COUNCIL_PDF_DIR}/：会議録の PDF")
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
    for it in ledgers:
        L.append(f"{it['title']}")
        L.append(f"  リポジトリ：{it['name']}")
        L.append(f"  版の番号：{it['commit']}")
        L.append(f"  版の日付：{jp_date(it['date'])}")
        L.append(f"  使い方：この版の一覧から、{SHIRYO_LIST_NAME} と、一式に入れる町の資料の原典を決めました（画面はありません）")
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
    for name in (PLANS_REPO, GIKAI_REPO, COUNCIL_REPO):
        if name not in dests:
            raise BundleError(f"{lock_path} に {name} がありません")

    # 出力先はリポジトリの外。町のホームページから取ったものの置き場所も、リポジトリの外
    town_dir = os.path.abspath(args.town_files or os.path.join(src, "temoto-town-files"))
    for r in [*repos, {"name": DOCS_REPO}]:
        try:
            rp = os.path.realpath(find_repo(r["name"], src))
        except BundleError:
            continue
        for what, p in (("出力先", out), ("町のホームページから取ったものの置き場所（--town-files）", town_dir)):
            if os.path.realpath(p) == rp or os.path.realpath(p).startswith(rp + os.sep):
                raise BundleError(f"{what} {p} が {r['name']} の中にあります。リポジトリの外を指定してください")
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
    council_meta = None
    commit_of = {}
    for r in repos:
        repo = find_repo(r["name"], src)
        date = check_commit(repo, r["name"], r["commit"])
        commit_of[r["name"]] = (repo, r["commit"])
        if r.get("make") in COUNCIL_MAKES:
            files, council_meta = make_council(repo, r["commit"])
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
    if council_meta is None:
        raise BundleError(f"{COUNCIL_REPO} の会議録の一覧を作れませんでした")

    # 2. 原典の一覧（台帳）と、手元にあるか
    plans_repo, plans_commit = commit_of[PLANS_REPO]
    plan_rows = read_ledger(git(plans_repo, "show", f"{plans_commit}:{PLANS_LEDGER}"),
                            ("id", "file", "url", "sha256"), f"{PLANS_REPO}/{PLANS_LEDGER}")
    led = next((x for x in lock["ledgers"] if x["name"] == DOCS_REPO), None)
    if led is None:
        raise BundleError(f"{lock_path} の ledgers に {DOCS_REPO} がありません")
    docs_repo = find_repo(DOCS_REPO, src)
    docs_commit = led["commit"]
    docs_date = check_commit(docs_repo, DOCS_REPO, docs_commit)
    ledger_items = [dict(led, date=docs_date, title=led.get("title", led["name"]))]
    doc_rows = read_ledger(git(docs_repo, "show", f"{docs_commit}:{led['use']}"),
                           ("id", "category", "title", "fiscal_year", "date", "url", "format", "sha256"),
                           f"{DOCS_REPO}/{led['use']}")
    gikai_repo, gikai_commit = commit_of[GIKAI_REPO]
    bulletins, photos = gikai_town_urls(gikai_repo, gikai_commit)
    plans_raw = os.path.abspath(args.plans_raw or os.path.join(plans_repo, "sources_raw"))
    docs_raw = os.path.abspath(args.docs_raw or os.path.join(docs_repo, "sources_raw"))
    council_pdf = os.path.abspath(args.council_pdf or os.path.join(commit_of[COUNCIL_REPO][0], COUNCIL_PDF_DIR))
    town = town_file_items(bulletins, photos, dests[GIKAI_REPO], town_dir)
    council = council_items(council_meta, dests[COUNCIL_REPO], council_pdf)
    genten = plan_items(plan_rows, plans_raw) + doc_items(doc_rows, docs_raw) + council + town
    check_items(genten)
    for it in genten:
        if it["dest"] in bundle:
            raise BundleError(f"{it['dest']} が {owner[it['dest']]} のファイルと重なります")
    print("原典の読み込み元：")
    print(f"  計画の原典：{plans_raw}（{PLANS_REPO} {plans_commit[:12]} の {PLANS_LEDGER}）")
    print(f"  町の資料：{docs_raw}（{DOCS_REPO} {docs_commit[:12]}（{jp_date(docs_date)}）の {led['use']}）")
    print(f"  会議録：{council_pdf}")
    print(f"  議会だより・議員の写真：{town_dir}")

    if args.fetch:
        print(f"町のホームページから取る（会議録の PDF・議会だより・議員の写真のうち、読み込み元・置き場所に無いもの。"
              f"{FETCH_INTERVAL:g} 秒に1件）：")
        got, failed, rest = fetch_files(town + council)
        print(f"  取ったもの {len(got)} 件、取れなかったもの {len(failed)} 件、取らなかったもの {len(rest)} 件")
        for it, why in failed[:10]:
            print(f"    - {it['url']}：{why}")
        if len(failed) > 10:
            print(f"    ほか {len(failed) - 10} 件")
        if rest:
            print("    取れなかったところで止めたので、残りは取っていません。時間をおいてもう一度動かすと、続きから取ります。")

    present, missing, mismatch = resolve_items(genten)
    if mismatch:
        print_items("中身が合わないので入れないもの：", mismatch)
        if args.on_mismatch != "skip":
            raise BundleError(f"中身が合わないものが {len(mismatch)} 件あります。入れずに続けるときは --on-mismatch skip を付けてください")
    if missing:
        print_items("手元に無いもの：", [(it, "") for it in missing])
        if not args.allow_missing:
            hint = ("（会議録の PDF と議会だより・議員の写真は --fetch で取れます）"
                    if any(it["kind"] in ("council", "bulletin", "photo") for it in missing) else "")
            raise BundleError(f"手元に無いものが {len(missing)} 件あります{hint}。無いものを飛ばして作るときは --allow-missing を付けてください")
    for name, root, kinds in ((KIND_NAME["plan"], plans_raw, ("plan",)), (KIND_NAME["doc"], docs_raw, ("doc",)),
                              (KIND_NAME["council"], council_pdf, ("council",)),
                              ("議会だより・議員の写真", town_dir, ("bulletin", "photo"))):
        extra = extra_files(root, {s for it in genten if it["kind"] in kinds for s in it["srcs"]})
        if extra:
            print(f"  参考：{name}の読み込み元にある、一覧に無いファイル（写さない）：{len(extra)} 件"
                  f"（例 {'、'.join(os.path.relpath(x, root) for x in extra[:3])}）")
    counts = summary_counts(genten, present)
    cat_names, unknown_cats = shiryo_cat_names(bundle, dests.get("hino-shiryo"), doc_rows)
    if unknown_cats:
        print(f"  参考：資料の一覧.csv で、町の資料の検索の画面に名前の無い分類は略のまま出す：{'、'.join(unknown_cats)}")
    fmap = file_map(present)
    known = {u for it in genten for u in [it["url"], *it.get("aliases", [])]}
    kind_of_dest = {it["dest"]: it["kind"] for it in present}

    # 3. リンクの書き換えと帯
    date_of = {it["name"]: it["date"] for it in items}
    state = bundled_state(counts)
    no_mark_of = {it["name"]: no_mark_css(it.get("no_mark", []), state) for it in items}
    rewritten, leftovers = 0, []
    local_log, online = [], []
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
        text = rewrite_local_files(text, base, fmap, known, protect_html=is_html, log=local_log, online=online)
        if is_html:
            try:
                text = inject(text, band_html(made, date_of[owner[p]]), no_mark_of[owner[p]])
            except BundleError as e:
                raise BundleError(f"{p}：{e}")
        bundle[p] = text.encode("utf-8")
    print(f"  公開版へのリンクを書き換えた数：{rewritten}")
    by_kind = {}
    for _, dest in local_log:
        by_kind[kind_of_dest[dest]] = by_kind.get(kind_of_dest[dest], 0) + 1
    print(f"  原典などへのリンクを手元のファイルに書き換えた数：{len(local_log)}（"
          + "、".join(f"{name} {by_kind.get(k, 0)}" for k, name in KINDS) + "）")
    print(f"  入れていないので町のホームページの URL のままにしたリンクの数：{len(online)}")

    # 書き換えなかったファイルの中の公開版の URL と、一式に入れたファイルの URL（データのファイルなど）
    present_urls = [u.encode() for u in fmap]
    for p in sorted(bundle):
        ext = posixpath.splitext(p)[1].lower()
        if ext in REWRITE_EXT:
            continue
        if PUBLIC_HOST.encode() in bundle[p]:
            leftovers.append((p, "公開版の URL がある（データのファイルなので書き換えていない）"))
        if b"shiga-hino.lg.jp" in bundle[p]:
            n = sum(bundle[p].count(u) for u in present_urls)
            if n:
                leftovers.append((p, f"一式に入れたファイルの URL が {n} か所ある（ページが読まないデータのファイルなので書き換えていない）"))

    write_files(out, bundle)
    copy_items(out, present)

    # 4. はじめにお読みください.txt、資料の一覧.csv、ファイルの一覧.csv
    readme = readme_text(made, items, counts, ledger_items)
    with open(os.path.join(out, PORTAL_DIR, README_NAME), "wb") as f:
        f.write(b"\xef\xbb\xbf" + readme.encode("utf-8"))
    with open(os.path.join(out, PORTAL_DIR, SHIRYO_LIST_NAME), "wb") as f:
        f.write(b"\xef\xbb\xbf" + shiryo_list_csv(doc_rows, present, cat_names).encode("utf-8"))
    csv_text, rows = file_list_csv(out)
    with open(os.path.join(out, PORTAL_DIR, FILELIST_NAME), "wb") as f:
        f.write(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))

    # 数字
    print("束ねた結果：")
    for it in items:
        pre = it["dest"] + "/"
        sub = [r for r in rows if r[0].startswith(pre)]
        if it["name"] == SELF_NAME:
            others = [x["dest"] + "/" for x in items if x["name"] != SELF_NAME]
            sub = [r for r in rows if r[0].startswith(pre) and not any(r[0].startswith(o) for o in others)]
        size = sum(r[1] for r in sub)
        print(f"  {it['name']:<26} {len(sub):>5} ファイル  {size:>14,} バイト（原典などを含む）")
    sizes = {r[0]: r[1] for r in rows}
    for k, name in KINDS:
        t, g = counts[k]
        size = sum(sizes.get(it["dest"], 0) for it in present if it["kind"] == k)
        print(f"  {name}：{t} 件のうち、入れたもの {g} 件（{size:,} バイト）、入れていないもの {t - g} 件")
    longest = max((r[0] for r in rows), key=len, default="")
    total = sum(r[1] for r in rows)
    print(f"  全体                       {len(rows):>5} ファイル  {total:>14,} バイト（{FILELIST_NAME} を除く）")
    print(f"  いちばん長いパス（出力先から）：{len(longest)} 字　{longest}")

    for p, why in leftovers:
        print(f"  参考：{p}：{why}")

    return check(out, args)


# 書き換えたリンクは、引用符・かっこ・= のすぐあとに、相対のパスとして置かれる。原典などのフォルダ（LOCAL_DIRS）を
# 1つの段として通るものを集める（文の中の引用符の組に頼らない）
LOCAL_REF_RE = re.compile(
    r"(?<=[\"'(=])((?:[^\s\"'<>`\\()=]*/)?(?:" + "|".join(map(re.escape, LOCAL_DIRS)) + r")/[^\s\"'<>`\\]+)")


def local_file_refs(text):
    """原典などのフォルダを通る相対のリンクを、出てきた数だけ集める"""
    res = []
    for m in LOCAL_REF_RE.finditer(text):
        v = m.group(1)
        if "://" in v or SCHEME_RE.match(v):
            continue
        res.append(v)
    return res


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
            data = fh.read(8)
            # 中を見る要るもの（Office の形式・圧縮・OLE）だけを全部読む。原典の PDF などは頭だけで足りる
            if (posixpath.splitext(f)[1].lower() in OOXML_EXT | OLE_EXT
                    or data[:4] in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0")):
                data += fh.read()
            why = forbidden_reason(f, data)
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

    # (b) の続き：ページとデータ（HTML と JavaScript）の中の、原典などへの相対のリンク（書き換えたもの）
    try:
        dests = dest_map(load_lock(os.path.abspath(args.lock))["repos"])
    except BundleError:
        dests = {}
    scripts = [f for f in files if posixpath.splitext(f)[1].lower() in REWRITE_EXT]
    nref, lbroken = 0, []
    for f in scripts:
        with open(os.path.join(out, f), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        refs = local_file_refs(text)
        if not refs:
            continue
        if posixpath.splitext(f)[1].lower() in (".html", ".htm"):
            base = posixpath.dirname(f)
        else:  # JavaScript は読み込むページの場所から（書き換えと同じ）
            base = max((d for d in dests.values() if f.startswith(d + "/")), key=len, default=posixpath.dirname(f))
        for v in sorted(set(refs)):
            nref += refs.count(v)
            why = check_ref(posixpath.join(base, "_"), v, exists)
            if why:
                lbroken.append((f, v, why))
    print(f"      原典・会議録・議会だより・議員の写真への手元のリンク（ページとデータの中）：{nref} か所を確かめ、"
          f"開けないもの {len(lbroken)} 件")
    for f, v, why in lbroken[:200]:
        print(f"      - {f}：{v}：{why}")
    if len(lbroken) > 200:
        print(f"      ほか {len(lbroken) - 200} 件")
    problems += len(lbroken)

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
    clip = sum(len(x["clipped"]) for x in res)
    band = max((x["bandLines360"] for x in res), default=0)
    wide_band = [x for x in res if x["bandLines360"] > BAND_MAX_LINES]
    print(f"  (c) 実ブラウザ（file://）で開いたページ：{len(res)} / {len(pages)}"
          f"（押したタブ {sum(x['tabs'] for x in res)}、開いた # の画面 {sum(x['hashes'] for x in res)}、"
          f"開かなかったページの中の場所への # {sum(x.get('hashesSkipped', 0) for x in res)}）")
    print(f"      外への通信：{req} 件")
    print(f"      JavaScript のエラー：{jserr} 件")
    print(f"      コンソールのエラー：{con} 件")
    print(f"      手元のファイルを読めなかったもの：{miss} 件")
    print(f"      開けなかったページ：{len(loaderr)} 件")
    print(f"      「（インターネット）」の印で字が切れるリンク（幅 1280px と 360px）：{clip} 件")
    print(f"      幅 360px での帯の行数：最大 {band} 行（{BAND_MAX_LINES} 行を超えたページ {len(wide_band)} 件）")
    for x in res:
        for kind, label in (("requests", "外への通信"), ("pageErrors", "JavaScript のエラー"),
                            ("consoleErrors", "コンソールのエラー"), ("failed", "読めなかったもの"),
                            ("clipped", "印で字が切れるリンク")):
            for v in x[kind]:
                print(f"      - {x['page']}：{label}：{v}")
        if x.get("loadError"):
            print(f"      - {x['page']}：開けなかった：{x['loadError']}")
        if x["bandLines360"] > BAND_MAX_LINES:
            print(f"      - {x['page']}：幅 360px で帯が {x['bandLines360']} 行")
    problems += req + jserr + con + miss + len(loaderr) + (len(pages) - len(res)) + clip + len(wide_band)
    return problems, True


def main(argv=None):
    ap = argparse.ArgumentParser(description="手元版（DESIGN.md 11章）を作る")
    ap.add_argument("--out", required=True, help="出力先（リポジトリの外のフォルダ）")
    ap.add_argument("--src", default=os.path.dirname(REPO_ROOT),
                    help="各リポジトリの取り出しの置き場所（既定は hino-portal の親のフォルダ）")
    ap.add_argument("--lock", default=os.path.join(REPO_ROOT, "bundle.lock.json"), help="版の記録（既定は bundle.lock.json）")
    ap.add_argument("--date", help="作った日（YYYY-MM-DD。既定は今日。日本時間）")
    ap.add_argument("--replace", action="store_true", help="出力先にある前の一式を消して作り直す")
    ap.add_argument("--docs-raw", help="町の資料の原典の読み込み元（既定は <src>/hino-town-docs/sources_raw。<id>.<拡張子> の形）")
    ap.add_argument("--plans-raw", help="計画の原典の読み込み元（既定は <src>/shiga-hino-plans/sources_raw。<id>/<file> の形）")
    ap.add_argument("--council-pdf", help="会議録の PDF の読み込み元（既定は <src>/hino-council-search/議事録本体。"
                                          "scripts/fetch-pdfs.mjs の置き方）")
    ap.add_argument("--town-files", help="議会だよりと議員の写真の置き場所（リポジトリの外。既定は <src>/temoto-town-files）")
    ap.add_argument("--fetch", action="store_true",
                    help="会議録の PDF と議会だより・議員の写真のうち、読み込み元・置き場所に無いものを町のホームページから取る（1秒に1件）")
    ap.add_argument("--allow-missing", action="store_true",
                    help="手元に無い原典・会議録・議会だより・写真を飛ばして作る（付けないときは、無いものがあれば止まる）")
    ap.add_argument("--on-mismatch", choices=("stop", "skip"), default="stop",
                    help="sha256 か中身の形が合わないものがあったとき、止まる（stop。既定）か、入れずに続ける（skip）か")
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
