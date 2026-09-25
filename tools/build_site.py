"""Collect the knowledge base into a MkDocs source folder.

Usage: python tools/build_site.py  (then: mkdocs build)
Markdown files keep their relative paths, so links between articles still work.
Links to non-Markdown files (e.g. prototype code) are rewritten to GitHub URLs.
"""
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_site_src")
REPO = "https://github.com/kouki0727mickey/addictive-game/blob/main"
SOURCES = ["README.md", "STRATEGY.md", "knowledge", "experiments", "prototype/README.md", "templates", "studio"]
LINK = re.compile(r"\]\(([^)\s]+)\)")


def rewrite(text, src_rel):
    def fix(m):
        target = m.group(1)
        if target.startswith(("http", "#", "mailto")):
            return m.group(0)
        path, _, anchor = target.partition("#")
        repo_path = os.path.normpath(os.path.join(os.path.dirname(src_rel), path))
        if path.endswith(".md") and os.path.exists(os.path.join(ROOT, repo_path)):
            if repo_path == "README.md":  # the top README becomes index.md
                rel = os.path.relpath("index.md", os.path.dirname(src_rel) or ".")
                return f"]({rel}{'#' + anchor if anchor else ''})"
            return m.group(0)
        return f"]({REPO}/{repo_path}{'#' + anchor if anchor else ''})"
    return LINK.sub(fix, text)


def copy_md(src_rel):
    dst_rel = "index.md" if src_rel == "README.md" else src_rel
    dst = os.path.join(OUT, dst_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(os.path.join(ROOT, src_rel), encoding="utf-8") as f:
        text = f.read()
    with open(dst, "w", encoding="utf-8") as f:
        f.write(rewrite(text, src_rel))


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    for src in SOURCES:
        full = os.path.join(ROOT, src)
        if os.path.isfile(full):
            copy_md(src)
            continue
        for dirpath, _, files in os.walk(full):
            for name in files:
                if name.endswith(".md"):
                    copy_md(os.path.relpath(os.path.join(dirpath, name), ROOT))
    print(f"collected into {OUT}")


if __name__ == "__main__":
    main()
