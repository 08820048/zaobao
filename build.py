#!/usr/bin/env python3
"""AI 早报静态站生成器.

读取每日早报 markdown（~/workspace/goals/daily-ai-news-digest/hidden_files/digest-YYYY-MM-DD.md），
生成 dist/ 下的静态 HTML：index.html（最新一期 + 往期归档）与每一天的独立页面。

无第三方依赖，方便定时任务直接运行：
    python3 ~/workspace/ai-zaobao/build.py
"""
import html
import os
import re
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
# 早报正文统一放在仓库的 content/ 下（digest-YYYY-MM-DD.md）；
# 每日定时任务会把新生成的早报拷进来再重新构建。
DIGEST_DIR = os.path.join(BASE, "content")
DIST = os.path.join(BASE, "dist")
SITE_NAME = "MuseAI 早报"
TAGLINE = "每天早上 · AI 科技资讯"

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

ARTICLE_RE = re.compile(r"^\*\*(\d+)\.\s*(.+?)\*\*\s*$")
TITLE_RE = re.compile(r"^#\s*(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def to_plain(text: str) -> str:
    """markdown 行内语法 → 分享用纯文本：[a](u) 变 a（u），**b** 变 b。"""
    text = LINK_RE.sub(lambda m: f"{m.group(1)}（{m.group(2)}）", text)
    text = BOLD_RE.sub(r"\1", text)
    return text


def article_plain_text(a: dict) -> str:
    """单条早报的分享纯文本：编号 + 标题 + 正文。"""
    parts = []
    num = f"{a['num']}." if a["num"] else ""
    head = f"{num} {to_plain(a['title'])}".strip()
    if head:
        parts.append(head)
    parts.extend(to_plain(p) for p in a["paras"])
    return "\n".join(parts)


def inline_format(text: str) -> str:
    """转义 HTML 后处理行内 markdown：链接与加粗。"""
    text = html.escape(text)
    # 先处理链接，避免链接文字里的 ** 被误处理
    parts = []
    last = 0
    for m in LINK_RE.finditer(text):
        parts.append(text[last:m.start()])
        label, url = m.group(1), m.group(2)
        # url 经过 escape 后 & 会变成 &amp;，在 href 里是合法的
        parts.append(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
        )
        last = m.end()
    parts.append(text[last:])
    text = "".join(parts)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    return text


def parse_digest(path: str, date_str: str) -> dict:
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    title = ""
    articles = []
    current = None
    para_buf = []

    def flush_para():
        if current is not None and para_buf:
            text = " ".join(para_buf).strip()
            if text:
                current["paras"].append(text)
            para_buf.clear()

    def flush_article():
        flush_para()
        if current is not None:
            articles.append(current)

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_para()
            continue
        m = TITLE_RE.match(line)
        if m and not title:
            title = m.group(1)
            continue
        m = ARTICLE_RE.match(line)
        if m:
            flush_article()
            current = {"num": m.group(1), "title": m.group(2), "paras": []}
            continue
        para_buf.append(line)
    flush_article()

    # 兜底：如果没解析出条目结构，把正文整体当一段渲染
    if not articles and title:
        body = " ".join(l.strip() for l in lines[1:] if l.strip())
        if body:
            articles = [{"num": "", "title": "", "paras": [body]}]

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return {
        "date": date_str,
        "display_date": f"{dt.month}月{dt.day}日",
        "weekday": f"星期{WEEKDAYS[dt.weekday()]}",
        "full_date": f"{dt.year} 年 {dt.month} 月 {dt.day} 日",
        "title": title or f"{dt.month}月{dt.day}日 {SITE_NAME}",
        "articles": articles,
    }


def render_article(a: dict, seq: int) -> str:
    try:
        num_txt = f"{int(a['num']):02d}"
    except (TypeError, ValueError):
        num_txt = str(a["num"] or "")
    num = f'<span class="story-num" aria-hidden="true">{html.escape(num_txt)}</span>'
    title = f"<h2>{inline_format(a['title'])}</h2>" if a["title"] else ""
    paras = "\n".join(f"<p>{inline_format(p)}</p>" for p in a["paras"])
    story_text = (
        f'<span class="story-text" hidden>{html.escape(article_plain_text(a))}</span>'
    )
    return (
        f'<article class="story" style="--i:{seq}">\n{num}\n'
        f'<div class="story-main">\n{title}\n{paras}\n{story_text}\n{STORY_COPY}\n</div>\n</article>'
    )


STORY_COPY = (
    '<button class="story-copy" type="button" aria-label="复制本条早报" title="复制本条早报">'
    '<span class="copy-ic" aria-hidden="true">'
    '<svg class="ic ic-copy" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="9" y="9" width="13" height="13" rx="2"/>'
    '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
    '<svg class="ic ic-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20 6L9 17l-5-5"/></svg>'
    "</span>"
    '<span class="visually-hidden copy-status" role="status"></span>'
    "</button>"
)

def issue_rail_html(digests: list, current_date: str) -> str:
    """左侧竖排期刊栏：新刊在上，标出当前页对应的一期。"""
    items = []
    for d in reversed(digests):
        is_cur = d["date"] == current_date
        cls = "rail-item is-current" if is_cur else "rail-item"
        cur = ' aria-current="page"' if is_cur else ""
        items.append(
            f'<li><a class="{cls}" href="/{d["date"]}.html"{cur}>'
            f'<span class="rail-date">{d["display_date"]}</span>'
            f'<span class="rail-sub">{d["weekday"]} · {len(d["articles"])} 条</span>'
            f"</a></li>"
        )
    return "\n".join(items)


PAGE_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title} · {site}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#f7f3e9" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#16130e" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='10' fill='%23b23a2c'/%3E%3Ctext x='32' y='46' font-size='34' text-anchor='middle' font-family='Songti SC, SimSun, serif' font-weight='bold' fill='%23f7f3e9'%3E%E6%97%A9%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="masthead">
  <div class="wrap">
    <p class="masthead-title"><a href="/">{site}</a></p>
    <p class="masthead-sub">{tagline}</p>
  </div>
  <div class="dateline"><div class="wrap dateline-in">
    <span class="dateline-left">{dateline_left}</span>
    <span class="dateline-right">{dateline_right}</span>
  </div></div>
</header>
<div class="wrap layout">
  <aside class="rail">
    <h2 class="rail-title">往期</h2>
    <ul>
{issue_rail}
    </ul>
  </aside>
  <main class="main-col">
{hidden_h1}
{body}
  </main>
</div>
<footer class="site-footer">
  <div class="wrap">
    <p>Made with Cerebellum</p>
    <a class="footer-social" href="https://x.com/xuyidev" target="_blank" rel="noopener noreferrer" aria-label="在 X 上关注 @xuyidev" title="在 X 上关注 @xuyidev">
      <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
    </a>
  </div>
</footer>
<script src="/site.js"></script>
</body>
</html>
"""

DAY_BODY_TMPL = """<div class="stream">
{cards}
</div>
<nav class="day-nav">
{prev_link}
{next_link}
</nav>
"""


def day_body(d: dict, prev: dict | None, nxt: dict | None) -> str:
    cards = "\n".join(render_article(a, i + 1) for i, a in enumerate(d["articles"]))
    prev_link = (
        f'<a class="nav-link" href="/{prev["date"]}.html">← {prev["display_date"]}</a>'
        if prev
        else '<span class="nav-link disabled">← 更早</span>'
    )
    next_link = (
        f'<a class="nav-link" href="/{nxt["date"]}.html">{nxt["display_date"]} →</a>'
        if nxt
        else '<a class="nav-link" href="/">最新 →</a>'
    )
    return DAY_BODY_TMPL.format(
        cards=cards,
        prev_link=prev_link,
        next_link=next_link,
    )


def index_body(digests: list) -> str:
    latest = digests[-1]
    cards = "\n".join(render_article(a, i + 1) for i, a in enumerate(latest["articles"]))
    return f"""<div class="stream">
{cards}
</div>
"""


def build() -> list:
    files = sorted(
        f for f in os.listdir(DIGEST_DIR) if re.fullmatch(r"digest-\d{4}-\d{2}-\d{2}\.md", f)
    )
    digests = []
    for f in files:
        date_str = f[len("digest-"):-len(".md")]
        try:
            digests.append(parse_digest(os.path.join(DIGEST_DIR, f), date_str))
        except Exception as e:  # noqa: BLE001 - 单个文件坏了不影响整站
            print(f"skip {f}: {e}", file=sys.stderr)
    if not digests:
        print("no digests found", file=sys.stderr)
        sys.exit(1)

    if not digests:
        print("no digests found", file=sys.stderr)
        sys.exit(1)

    # 按日期先后编期号
    for i, d in enumerate(digests):
        d["issue"] = i + 1

    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)

    # 每天的独立页面
    for i, d in enumerate(digests):
        prev = digests[i - 1] if i > 0 else None
        nxt = digests[i + 1] if i < len(digests) - 1 else None
        body = day_body(d, prev, nxt)
        page = PAGE_TMPL.format(
            page_title=d["title"],
            site=SITE_NAME,
            tagline=TAGLINE,
            desc=f"{d['full_date']} AI 科技早报，共 {len(d['articles'])} 条重要资讯。",
            dateline_left=f'{d["full_date"]} · {d["weekday"]}',
            dateline_right=f'第 {d["issue"]} 期',
            issue_rail=issue_rail_html(digests, d["date"]),
            hidden_h1=f'<h1 class="visually-hidden">{html.escape(d["title"])}</h1>',
            body=body,
        )
        with open(os.path.join(DIST, f"{d['date']}.html"), "w", encoding="utf-8") as f:
            f.write(page)

    # 首页：最新一期 + 归档
    latest = digests[-1]
    index_page = PAGE_TMPL.format(
        page_title="最新",
        site=SITE_NAME,
        tagline=TAGLINE,
        desc="每天早上更新的 AI 科技资讯早报：大模型动态、芯片算力、政策监管、融资并购、开源项目与 AI 应用。",
        dateline_left=f'{latest["full_date"]} · {latest["weekday"]}',
        dateline_right=(
            f'<span class="stamp">最新</span><span>第 {latest["issue"]} 期</span>'
        ),
        issue_rail=issue_rail_html(digests, latest["date"]),
        hidden_h1=f'<h1 class="visually-hidden">{SITE_NAME} — {TAGLINE}</h1>',
        body=index_body(digests),
    )
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)

    shutil.copy(os.path.join(BASE, "style.css"), os.path.join(DIST, "style.css"))
    shutil.copy(os.path.join(BASE, "site.js"), os.path.join(DIST, "site.js"))
    print(f"built {len(digests)} digests -> {DIST}")
    return digests


if __name__ == "__main__":
    build()
