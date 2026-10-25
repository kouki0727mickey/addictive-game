"""課題の説明（Markdown）を、Jira の書式に変換する。

- Jira Cloud（REST v3）: Atlassian Document Format（ADF。JSON の文書木）
- Jira Data Center / Server（REST v2）: Wiki 記法

対応する Markdown は、課題の説明に出るものに絞る:
見出し、段落、箇条書き・番号付き（入れ子）、引用、コードブロック、表、太字・斜体・コード・リンク・<br>。
"""

from __future__ import annotations

import re

_INLINE = re.compile(r"(\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)|(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])|<br\s*/?>)")
_LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


def _split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells = re.split(r"(?<!\\)\|", s)
    return [c.strip().replace("\\|", "|") for c in cells]


def parse_blocks(md: str) -> list[dict]:
    """Markdown を、変換先に依らない中間の木にする。"""
    lines = md.replace("\r\n", "\n").split("\n")
    blocks: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            blocks.append({"t": "code", "lang": lang, "text": "\n".join(body)})
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            blocks.append({"t": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]):
            header = _split_row(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append({"t": "table", "header": header, "rows": rows})
            continue
        if line.lstrip().startswith(">"):
            quote = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append({"t": "quote", "children": parse_blocks("\n".join(quote))})
            continue
        if _LIST.match(line):
            items = []
            while i < len(lines) and (_LIST.match(lines[i]) or (lines[i].startswith("  ") and lines[i].strip() and items)):
                m = _LIST.match(lines[i])
                if m and items and len(m.group(1).expandtabs(4)) <= items[0]["indent"] and m.group(2)[0].isdigit() != items[0]["ordered"]:
                    break  # 同じ深さで箇条書きと番号付きが切り替わったら、別のリストにする
                if m:
                    items.append({"indent": len(m.group(1).expandtabs(4)), "ordered": m.group(2)[0].isdigit(), "text": m.group(3)})
                else:
                    items[-1]["text"] += "\n" + lines[i].strip()  # 項目の続きの行
                i += 1
            blocks.append(_nest_list(items))
            continue
        para = [line.strip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not (
            _LIST.match(lines[i]) or lines[i].lstrip().startswith(("#", ">", "|", "```"))
        ):
            para.append(lines[i].strip())
            i += 1
        blocks.append({"t": "para", "text": "\n".join(para)})
    return blocks


def _nest_list(items: list[dict]) -> dict:
    """字下げの深さから入れ子のリストを組み立てる。"""
    root = {"t": "list", "ordered": items[0]["ordered"], "items": [], "indent": items[0]["indent"]}
    stack = [root]
    for it in items:
        while len(stack) > 1 and it["indent"] < stack[-1]["indent"]:
            stack.pop()
        cur = stack[-1]
        if it["indent"] > cur["indent"] and cur["items"]:
            sub = {"t": "list", "ordered": it["ordered"], "items": [], "indent": it["indent"]}
            cur["items"][-1]["children"].append(sub)
            stack.append(sub)
            cur = sub
        cur["items"].append({"text": it["text"], "children": []})
    return root


# ---------------------------------------------------------------- ADF


def _adf_inline(text: str) -> list[dict]:
    out: list[dict] = []
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            out += _adf_text(text[pos : m.start()])
        if m.group(2) is not None:
            out += [dict(n, marks=n.get("marks", []) + [{"type": "strong"}]) for n in _adf_inline(m.group(2))]
        elif m.group(3) is not None:
            out.append({"type": "text", "text": m.group(3), "marks": [{"type": "code"}]})
        elif m.group(4) is not None:
            out.append({"type": "text", "text": m.group(4), "marks": [{"type": "link", "attrs": {"href": m.group(5)}}]})
        elif m.group(6) is not None:
            out += [dict(n, marks=n.get("marks", []) + [{"type": "em"}]) for n in _adf_inline(m.group(6))]
        else:
            out.append({"type": "hardBreak"})
        pos = m.end()
    if pos < len(text):
        out += _adf_text(text[pos:])
    # hardBreak に marks は付けられない
    return [{k: v for k, v in n.items() if not (k == "marks" and (not v or n["type"] == "hardBreak"))} for n in out]


def _adf_text(text: str) -> list[dict]:
    out = []
    for j, part in enumerate(text.split("\n")):
        if j:
            out.append({"type": "hardBreak"})
        if part:
            out.append({"type": "text", "text": part})
    return out


def _adf_block(b: dict) -> list[dict]:
    t = b["t"]
    if t == "heading":
        return [{"type": "heading", "attrs": {"level": b["level"]}, "content": _adf_inline(b["text"]) or [{"type": "text", "text": " "}]}]
    if t == "para":
        content = _adf_inline(b["text"])
        return [{"type": "paragraph", "content": content}] if content else []
    if t == "code":
        node = {"type": "codeBlock", "content": [{"type": "text", "text": b["text"]}] if b["text"] else []}
        if b["lang"]:
            node["attrs"] = {"language": b["lang"]}
        return [node]
    if t == "quote":
        inner = [n for c in b["children"] for n in _adf_block(c) if n["type"] in ("paragraph", "bulletList", "orderedList", "codeBlock")]
        return [{"type": "blockquote", "content": inner}] if inner else []
    if t == "list":
        items = []
        for it in b["items"]:
            content = [{"type": "paragraph", "content": _adf_inline(it["text"]) or [{"type": "text", "text": " "}]}]
            for c in it["children"]:
                content += _adf_block(c)
            items.append({"type": "listItem", "content": content})
        return [{"type": "orderedList" if b["ordered"] else "bulletList", "content": items}]
    if t == "table":
        width = max([len(b["header"])] + [len(r) for r in b["rows"]])

        def row(cells, cell_type):
            cells = cells + [""] * (width - len(cells))
            return {
                "type": "tableRow",
                "content": [{"type": cell_type, "content": [{"type": "paragraph", "content": _adf_inline(c)}]} for c in cells],
            }

        return [{"type": "table", "content": [row(b["header"], "tableHeader")] + [row(r, "tableCell") for r in b["rows"]]}]
    return []


def to_adf(md: str) -> dict:
    content = [n for b in parse_blocks(md) for n in _adf_block(b)]
    return {"type": "doc", "version": 1, "content": content or [{"type": "paragraph", "content": []}]}


# ---------------------------------------------------------------- Wiki 記法（v2）


def _wiki_escape(text: str) -> str:
    return re.sub(r"([{}\[\]|])", r"\\\1", text)


def _wiki_inline(text: str) -> str:
    out = []
    pos = 0
    for m in _INLINE.finditer(text):
        out.append(_wiki_escape(text[pos : m.start()]))
        if m.group(2) is not None:
            out.append(f"*{_wiki_inline(m.group(2))}*")
        elif m.group(3) is not None:
            out.append("{{" + m.group(3) + "}}")
        elif m.group(4) is not None:
            out.append(f"[{_wiki_escape(m.group(4))}|{m.group(5)}]")
        elif m.group(6) is not None:
            out.append(f"_{_wiki_inline(m.group(6))}_")
        else:
            out.append("\\\\ ")
        pos = m.end()
    out.append(_wiki_escape(text[pos:]))
    return "".join(out).replace("\n", "\\\\ ")


def _wiki_list(b: dict, prefix: str = "") -> list[str]:
    lines = []
    mark = prefix + ("#" if b["ordered"] else "*")
    for it in b["items"]:
        lines.append(f"{mark} {_wiki_inline(it['text'])}")
        for c in it["children"]:
            lines += _wiki_list(c, mark) if c["t"] == "list" else [_wiki_block(c)]
    return lines


def _wiki_block(b: dict) -> str:
    t = b["t"]
    if t == "heading":
        return f"h{b['level']}. {_wiki_inline(b['text'])}"
    if t == "para":
        return _wiki_inline(b["text"])
    if t == "code":
        return "{code" + (f":{b['lang']}" if b["lang"] else "") + "}\n" + b["text"] + "\n{code}"
    if t == "quote":
        return "{quote}\n" + "\n\n".join(_wiki_block(c) for c in b["children"]) + "\n{quote}"
    if t == "list":
        return "\n".join(_wiki_list(b))
    if t == "table":
        lines = ["||" + "||".join(_wiki_inline(c) or " " for c in b["header"]) + "||"]
        lines += ["|" + "|".join(_wiki_inline(c) or " " for c in r) + "|" for r in b["rows"]]
        return "\n".join(lines)
    return ""


def to_wiki(md: str) -> str:
    return "\n\n".join(s for s in (_wiki_block(b) for b in parse_blocks(md)) if s)
