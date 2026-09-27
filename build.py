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
SITE_NAME = "AI 早报"
TAGLINE = "每天早上 · AI 科技资讯"

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

ARTICLE_RE = re.compile(r"^\*\*(\d+)\.\s*(.+?)\*\*\s*$")
TITLE_RE = re.compile(r"^#\s*(.+?)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


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
        "title": title or f"{dt.month}月{dt.day}日 AI 早报",
        "articles": articles,
    }


def render_article(a: dict) -> str:
    num = f'<span class="num">{html.escape(a["num"])}</span>' if a["num"] else ""
    title = f"<h2>{inline_format(a['title'])}</h2>" if a["title"] else ""
    paras = "\n".join(f"<p>{inline_format(p)}</p>" for p in a["paras"])
    return f'<article class="card">\n{num}\n{title}\n{paras}\n</article>'


PAGE_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title} · {site}</title>
<meta name="description" content="{desc}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23f2a93b'/%3E%3Ctext x='32' y='42' font-size='28' text-anchor='middle' font-family='sans-serif' font-weight='bold' fill='%23101418'%3EAI%3C/text%3E%3C/svg%3E">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<div class="topbar"></div>
<header class="site-header">
  <div class="wrap header-in">
    <a class="brand" href="/">{site}</a>
    <span class="tagline">{tagline}</span>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>内容由 Muse 每日自动生成 · 部署于 Cloudflare Pages</p>
  </div>
</footer>
</body>
</html>
"""

DAY_BODY_TMPL = """<p class="date-label">{full_date} · {weekday}</p>
<h1 class="day-title">{title}</h1>
<div class="cards">
{cards}
</div>
<nav class="day-nav">
{prev_link}
{next_link}
</nav>
"""


def day_body(d: dict, prev: dict | None, nxt: dict | None) -> str:
    cards = "\n".join(render_article(a) for a in d["articles"])
    prev_link = (
        f'<a class="nav-btn" href="/{prev["date"]}.html">← {prev["display_date"]}</a>'
        if prev
        else '<span class="nav-btn disabled">← 更早</span>'
    )
    next_link = (
        f'<a class="nav-btn" href="/{nxt["date"]}.html">{nxt["display_date"]} →</a>'
        if nxt
        else '<a class="nav-btn" href="/">最新 →</a>'
    )
    return DAY_BODY_TMPL.format(
        full_date=d["full_date"],
        weekday=d["weekday"],
        title=html.escape(d["title"]),
        cards=cards,
        prev_link=prev_link,
        next_link=next_link,
    )


def index_body(digests: list) -> str:
    latest = digests[-1]
    cards = "\n".join(render_article(a) for a in latest["articles"])
    items = []
    for d in reversed(digests):
        count = len(d["articles"])
        items.append(
            f'<li><a href="/{d["date"]}.html">'
            f'<span class="arch-date">{d["full_date"]} · {d["weekday"]}</span>'
            f'<span class="arch-title">{html.escape(d["title"])}</span>'
            f'<span class="arch-count">{count} 条</span>'
            f"</a></li>"
        )
    archive = "\n".join(items)
    return f"""<p class="date-label">{latest["full_date"]} · {latest["weekday"]} · 最新</p>
<h1 class="day-title">{html.escape(latest["title"])}</h1>
<div class="cards">
{cards}
</div>
<section class="archive">
  <h2>往期早报</h2>
  <ul>
{archive}
  </ul>
</section>
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
            body=body,
        )
        with open(os.path.join(DIST, f"{d['date']}.html"), "w", encoding="utf-8") as f:
            f.write(page)

    # 首页：最新一期 + 归档
    index_page = PAGE_TMPL.format(
        page_title="最新",
        site=SITE_NAME,
        tagline=TAGLINE,
        desc="每天早上更新的 AI 科技资讯早报：大模型动态、芯片算力、政策监管、融资并购、开源项目与 AI 应用。",
        body=index_body(digests),
    )
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_page)

    shutil.copy(os.path.join(BASE, "style.css"), os.path.join(DIST, "style.css"))
    print(f"built {len(digests)} digests -> {DIST}")
    return digests


if __name__ == "__main__":
    build()
