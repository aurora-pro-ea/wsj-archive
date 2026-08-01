from __future__ import annotations

import html
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from extra_articles import parse_extra_articles
from wechat_imports import parse_downloaded_articles, title_key


ROOT = Path(__file__).resolve().parent
OUT = Path(__file__).resolve().parent / "dist"
SITE_URL = "https://wushujian.pages.dev"
SOURCE_FILES = [
    ROOT / "2024年文章整理.md",
    ROOT / "2025年图片文章整理.md",
    ROOT / "2026年图片文章整理.md",
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def slug_for(year: int, article_date: str, ordinal: int) -> str:
    return f"{year}-{article_date[5:]}-{ordinal:03d}"


def inline_md(text: str) -> str:
    value = esc(text.strip())
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', value)
    return value


def render_fragment(lines: list[str]) -> tuple[str, list[tuple[str, str]]]:
    blocks: list[str] = []
    toc: list[tuple[str, str]] = []
    paragraph: list[str] = []
    quote: list[str] = []
    list_items: list[str] = []
    heading_number = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = "".join(part.strip() for part in paragraph).strip()
            if text:
                blocks.append(f"<p>{inline_md(text)}</p>")
        paragraph = []

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            text = "<br>".join(inline_md(part) for part in quote)
            blocks.append(f"<blockquote>{text}</blockquote>")
        quote = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            body = "".join(f"<li>{inline_md(item)}</li>" for item in list_items)
            blocks.append(f"<ol>{body}</ol>")
        list_items = []

    for raw in lines:
        line = raw.strip()
        if not line or line == "---":
            flush_paragraph()
            flush_quote()
            flush_list()
            continue
        if line.startswith("### "):
            flush_paragraph()
            flush_quote()
            flush_list()
            heading = line[4:].strip()
            heading_number += 1
            anchor = f"section-{heading_number}"
            toc.append((anchor, heading))
            blocks.append(f'<h3 id="{anchor}">{inline_md(heading)}</h3>')
            continue
        if line.startswith("> ") or line == ">":
            flush_paragraph()
            flush_list()
            quote.append(line[2:] if line.startswith("> ") else "")
            continue
        list_match = re.match(r"^(?:[-*]|\d+[.)])\s+(.+)$", line)
        if list_match:
            flush_paragraph()
            flush_quote()
            list_items.append(list_match.group(1))
            continue
        flush_quote()
        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_quote()
    flush_list()
    return "\n".join(blocks), toc


def parse_file(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    matches = list(
        re.finditer(r"^##\s+(\d{4}-\d{2}-\d{2})｜(.+?)\s*$", "\n".join(lines), re.M)
    )
    articles: list[dict] = []
    year = int(path.name[:4])
    for match in matches:
        start = match.end()
        next_match = next((m for m in matches if m.start() > match.start()), None)
        end = next_match.start() if next_match else len("\n".join(lines))
        raw_body = "\n".join(lines)[start:end]
        raw_body = re.sub(r"^\s*---\s*$", "", raw_body, flags=re.M)
        body_lines = raw_body.strip().splitlines()
        article_date = match.group(1)
        title = match.group(2).strip()
        text = " ".join(line.strip() for line in body_lines if line.strip())
        articles.append(
            {
                "year": year,
                "date": article_date,
                "month": int(article_date[5:7]),
                "title": title,
                "body_lines": body_lines,
                "text": text,
            }
        )
    return articles


def make_excerpt(text: str, length: int = 120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= length else text[:length].rstrip() + "…"


def shell_page(title: str, description: str, body: str, active_year: str = "") -> str:
    year_links = []
    for year in (2024, 2025, 2026):
        active = ' class="active"' if str(year) == active_year else ""
        year_links.append(f'<a{active} href="/{year}/">{year}</a>')
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} · WSJ文章档案</title>
  <meta name="description" content="{esc(description)}">
  <meta name="theme-color" content="#171717">
  <link rel="stylesheet" href="/assets/style.css">
  <link rel="manifest" href="/site.webmanifest">
</head>
<body>
  <div class="reading-progress" id="reading-progress"></div>
  <header class="site-header">
    <div class="header-inner">
      <a class="brand" href="/">WSJ<span>·</span>文章档案</a>
      <nav class="year-nav" aria-label="年度导航">{''.join(year_links)}</nav>
      <div class="header-actions">
        <label class="search-box" aria-label="搜索文章">
          <span aria-hidden="true">⌕</span>
          <input id="site-search" type="search" placeholder="搜索标题或正文" autocomplete="off">
        </label>
        <button class="icon-button" id="theme-toggle" type="button" aria-label="切换深色模式">☾</button>
        <button class="icon-button menu-button" id="menu-toggle" type="button" aria-label="打开菜单">☰</button>
      </div>
    </div>
    <div class="search-panel" id="search-panel" hidden>
      <div class="search-panel-meta" id="search-meta"></div>
      <div id="search-results" class="search-results"></div>
    </div>
  </header>
  <main>{body}</main>
  <footer class="site-footer">
    <div>WSJ文章档案 · 2024—2026</div>
    <div>静态发布 · 适配桌面与移动设备</div>
  </footer>
  <script src="/assets/script.js" defer></script>
</body>
</html>'''


def article_card(article: dict) -> str:
    return f'''<article class="article-card" data-year="{article['year']}" data-month="{article['month']}" data-search="{esc(article['title'] + ' ' + article['text'])}">
  <div class="card-date">{article['date']}</div>
  <h3><a href="{article['url']}">{esc(article['title'])}</a></h3>
  <p>{esc(make_excerpt(article['text']))}</p>
  <a class="read-more" href="{article['url']}">继续阅读 <span>→</span></a>
</article>'''


def month_label(month: int) -> str:
    return f"{month:02d}月"


def build() -> tuple[list[dict], Path]:
    # Keep hand-maintained static assets (CSS, JS, and Cloudflare headers)
    # when rebuilding the generated HTML/data files.
    if OUT.exists():
        for child in OUT.iterdir():
            if child.name in {"assets", "_headers"}:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    (OUT / "assets").mkdir(parents=True, exist_ok=True)

    articles: list[dict] = []
    for source in SOURCE_FILES:
        articles.extend(parse_file(source))
    articles.extend(parse_extra_articles())
    downloaded_articles = parse_downloaded_articles(ROOT / "wechat-imports")
    downloaded_keys = {(article["year"], title_key(article["title"])) for article in downloaded_articles}
    articles = [
        article
        for article in articles
        if (article["year"], title_key(article["title"])) not in downloaded_keys
    ]
    articles.extend(downloaded_articles)
    articles.sort(key=lambda item: (item["date"], item["title"]))

    counters: defaultdict[int, int] = defaultdict(int)
    for article in articles:
        counters[article["year"]] += 1
        article["ordinal"] = counters[article["year"]]
        article["slug"] = slug_for(article["year"], article["date"], article["ordinal"])
        article["url"] = f"/articles/{article['slug']}/"
        article["html_body"], article["toc"] = render_fragment(article["body_lines"])
        if not article["html_body"]:
            # Keep malformed/OCR-only headings from opening as a visually blank page.
            article["text"] = "该条目未识别到有效正文内容。"
            article["html_body"] = "<p>该条目未识别到有效正文内容。</p>"

    by_year: defaultdict[int, list[dict]] = defaultdict(list)
    for article in articles:
        by_year[article["year"]].append(article)

    # Search index: body text is intentionally omitted to keep the initial payload small.
    search_index = [
        {
            "year": a["year"],
            "date": a["date"],
            "month": a["month"],
            "title": a["title"],
            "excerpt": make_excerpt(a["text"]),
            "url": a["url"],
            "search": (a["title"] + " " + a["text"])[:1800],
        }
        for a in articles
    ]
    (OUT / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    stats = "".join(
        f'<div class="stat"><strong>{len(by_year[year])}</strong><span>{year}年文章</span></div>'
        for year in (2024, 2025, 2026)
    )
    latest = "".join(article_card(a) for a in reversed(articles[-12:]))
    home_body = f'''<section class="hero-wrap">
  <div class="hero-copy">
    <p class="eyebrow">PERSONAL ARCHIVE · 2024—2026</p>
    <h1>把文章，<em>留在时间里。</em></h1>
    <p class="hero-lede">三年的文字，按日期、主题和阅读路径重新编排。适合慢慢读，也方便随时查找。</p>
    <div class="hero-actions"><a class="button primary" href="/2026/">浏览最新文章</a><a class="button ghost" href="#latest">查看最近更新</a></div>
  </div>
  <div class="hero-mark"><span>WSJ</span><small>READ<br>THINK<br>REMEMBER</small></div>
</section>
<section class="stats-row" aria-label="文章统计">{stats}<div class="stat"><strong>{len(articles)}</strong><span>篇文章</span></div></section>
<section class="archive-intro">
  <div><p class="eyebrow">ARCHIVE MAP</p><h2>按年份进入</h2></div>
  <p>每篇文章都有独立地址；年度页按月份分组，文章页保留章节锚点，手机端也能快速跳转。</p>
</section>
<section class="year-grid">{''.join(f'<a class="year-card year-{year}" href="/{year}/"><span>{year}</span><small>{len(by_year[year])} 篇 · 按月浏览</small><b>进入档案 →</b></a>' for year in (2024, 2025, 2026))}</section>
<section class="section-heading" id="latest"><div><p class="eyebrow">LATEST NOTES</p><h2>最近更新</h2></div><a href="/2026/">查看 2026 全部 →</a></section>
<section class="article-grid">{latest}</section>'''
    (OUT / "index.html").write_text(
        shell_page("首页", "2024—2026 年度文章档案，按日期与月份浏览。", home_body),
        encoding="utf-8",
    )

    for year in (2024, 2025, 2026):
        year_articles = by_year[year]
        months: defaultdict[int, list[dict]] = defaultdict(list)
        for article in year_articles:
            months[article["month"]].append(article)
        month_nav = "".join(
            f'<a href="#month-{year}-{month}">{month_label(month)}</a>' for month in sorted(months)
        )
        sections = []
        for month in sorted(months):
            cards = "".join(article_card(a) for a in months[month])
            sections.append(
                f'<section class="month-section" id="month-{year}-{month}"><div class="month-heading"><h2>{month_label(month)}</h2><span>{len(months[month])} 篇</span></div><div class="article-grid">{cards}</div></section>'
            )
        year_body = f'''<section class="archive-hero year-hero-{year}">
  <p class="eyebrow">YEAR ARCHIVE</p><h1>{year}</h1><p>{len(year_articles)} 篇文章，按月份编排。</p>
</section>
<nav class="month-nav" aria-label="月份导航">{month_nav}</nav>
<div class="archive-toolbar"><span>点击标题进入独立阅读页</span><a href="/">← 返回总览</a></div>
{''.join(sections)}'''
        year_dir = OUT / str(year)
        year_dir.mkdir(parents=True)
        (year_dir / "index.html").write_text(
            shell_page(f"{year}年文章", f"{year} 年文章档案，共 {len(year_articles)} 篇。", year_body, str(year)),
            encoding="utf-8",
        )

    for article in articles:
        toc_links = "".join(f'<a href="#{anchor}">{esc(label)}</a>' for anchor, label in article["toc"])
        current_index = articles.index(article)
        prev_article = articles[current_index - 1] if current_index > 0 else None
        next_article = None
        if current_index + 1 < len(articles):
            next_article = articles[current_index + 1]
        article_body = f'''<div class="article-layout">
  <aside class="article-sidebar"><a class="back-link" href="/{article['year']}/">← {article['year']} 年档案</a><div class="toc-label">本文目录</div><nav class="article-toc">{toc_links or '<span>正文</span>'}</nav></aside>
  <article class="reading-article">
    <div class="article-kicker">{article['date']} · {article['year']} ARCHIVE</div>
    <h1>{esc(article['title'])}</h1>
    <div class="article-meta"><span>WSJ文章档案</span><span>·</span><span>阅读时间取决于你的思考速度</span></div>
    <div class="article-content">{article['html_body']}</div>
    <div class="article-footer-nav">{f'<a href="{prev_article["url"]}">← {esc(prev_article["title"])}</a>' if prev_article else '<span></span>'}{f'<a href="{next_article["url"]}">{esc(next_article["title"])} →</a>' if next_article else '<span></span>'}</div>
  </article>
</div>'''
        article_dir = OUT / "articles" / article["slug"]
        article_dir.mkdir(parents=True)
        (article_dir / "index.html").write_text(
            shell_page(article["title"], make_excerpt(article["text"], 160), article_body, str(article["year"])),
            encoding="utf-8",
        )

    (OUT / "404.html").write_text(
        shell_page("页面未找到", "你访问的文章页面不存在。", '<section class="not-found"><p class="eyebrow">404</p><h1>这篇文章走丢了。</h1><p>可以返回年度档案，或者用顶部搜索重新查找。</p><a class="button primary" href="/">回到首页</a></section>'),
        encoding="utf-8",
    )
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", encoding="utf-8")
    sitemap_urls = ["/", "/2024/", "/2025/", "/2026/"] + [a["url"] for a in articles]
    sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" + "".join(f"<url><loc>{SITE_URL}{u}</loc></url>" for u in sitemap_urls) + "</urlset>\n"
    (OUT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (OUT / "site.webmanifest").write_text(json.dumps({"name": "WSJ文章档案", "short_name": "WSJ档案", "start_url": "/", "display": "standalone", "background_color": "#f4f0e8", "theme_color": "#171717", "lang": "zh-CN"}, ensure_ascii=False), encoding="utf-8")
    (OUT / "favicon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#171717"/><text x="7" y="42" fill="#f7f2e9" font-size="21" font-family="Georgia,serif">WSJ</text></svg>', encoding="utf-8")
    return articles, OUT


if __name__ == "__main__":
    built, output = build()
    print(f"Built {len(built)} articles into {output}")
