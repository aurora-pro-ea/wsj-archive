from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path


def internal_target(root: Path, href: str) -> Path | None:
    if not href.startswith("/") or href.startswith("//"):
        return None
    path = href.split("#", 1)[0].split("?", 1)[0]
    if path == "/":
        return root / "index.html"
    if path.endswith("/"):
        return root / path.lstrip("/") / "index.html"
    return root / path.lstrip("/")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "dist").resolve()
    errors: list[str] = []
    required = [
        "index.html",
        "2024/index.html",
        "2025/index.html",
        "2026/index.html",
        "assets/style.css",
        "assets/script.js",
        "search-index.json",
        "sitemap.xml",
        "_headers",
    ]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    index_path = root / "search-index.json"
    records = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    article_pages = list((root / "articles").glob("*/index.html"))
    if len(records) != len(article_pages):
        errors.append(f"article count mismatch: index={len(records)}, html={len(article_pages)}")

    content_pattern = re.compile(
        r'<div class="article-content">(.*?)</div>\s*<div class="article-footer-nav">',
        re.S,
    )
    for page in article_pages:
        source = page.read_text(encoding="utf-8")
        match = content_pattern.search(source)
        text = html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip() if match else ""
        if not text:
            errors.append(f"empty article body: {page.relative_to(root).as_posix()}")

    for page in root.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', source):
            target = internal_target(root, href)
            if target is not None and not target.exists():
                errors.append(f"broken link: {page.relative_to(root).as_posix()} -> {href}")

    sitemap_path = root / "sitemap.xml"
    sitemap = sitemap_path.read_text(encoding="utf-8") if sitemap_path.exists() else ""
    if "__SITE_URL__" in sitemap:
        errors.append("sitemap still contains __SITE_URL__ placeholder")

    if errors:
        print("Validation failed:")
        for error in errors[:50]:
            print(f"- {error}")
        if len(errors) > 50:
            print(f"- ... and {len(errors) - 50} more")
        return 1

    print(f"Validation passed: {len(records)} articles, {len(list(root.rglob('*')))} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
