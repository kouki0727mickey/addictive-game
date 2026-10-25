"""段階1: PowerPoint (.pptx) から、テキスト・表・グラフ・SmartArt・画像・ノートを構造のまま取り出す。

出力（--out のディレクトリ）:
  slides.json    スライドごとの構造化データ（後段の正本）
  extracted.md   抽出結果だけで作った決定的な Markdown（VLM が使えないときの代わり・比較の基準）
  images/        埋め込み画像（内容のハッシュで重複を除く）
  renders/       スライド全体の画像（LibreOffice → PDF → PNG）。VLM にレイアウトを見せるため

アルゴリズムの要点:
  - 読む順序は再帰 XY-cut（図形の外接矩形を、空白の帯で上下→左右に再帰的に切る）。
    座標の (top, left) で並べるだけだと、2段組みや横並びの箱で順序が崩れる
  - グループ図形は子の座標を、グループの座標系（chOff/chExt → off/ext）で変換してから並べる
  - 箇条書きの記号・番号・階層は段落の XML（buChar / buAutoNum / buNone と lvl）から読む
  - 表の結合セルは起点のセルだけに値を入れる（同じ文字を繰り返すと課題が重複するため）
  - SmartArt はデータ部（dgm:dataModel）の点と親子の接続から、階層つきの項目に戻す
  - 小さすぎる画像と、半数以上のスライドに繰り返し出る画像（ロゴ）は装飾として扱う
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.shapes.picture import Picture
from pptx.util import Emu

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import md_escape_cell, sha256_of, write_json  # noqa: E402

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "dgm": "http://schemas.openxmlformats.org/drawingml/2006/diagram",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
}
DIAGRAM_URI = "http://schemas.openxmlformats.org/drawingml/2006/diagram"

# 本文ではない飾りのプレースホルダ（スライド番号・日付・フッター）
SKIP_PLACEHOLDERS = {PP_PLACEHOLDER.SLIDE_NUMBER, PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.HEADER}
TITLE_PLACEHOLDERS = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE}
# 行頭記号を明示しなくても箇条書きになるプレースホルダ
BULLETED_PLACEHOLDERS = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.VERTICAL_BODY, PP_PLACEHOLDER.VERTICAL_OBJECT}

MIN_IMAGE_AREA_RATIO = 0.004  # スライド面積の 0.4% 未満は装飾（アイコン・区切り線）
MIN_IMAGE_PX = 40
REPEATED_IMAGE_RATIO = 0.5  # 半数以上のスライドに出る同じ画像はロゴ扱い
VLM_IMAGE_FORMATS = {"png", "jpeg", "jpg", "gif", "bmp", "webp"}


# ---------------------------------------------------------------- 座標


class Transform:
    """グループの子の座標 → スライド座標。入れ子のグループは合成する。"""

    def __init__(self, sx=1.0, sy=1.0, tx=0.0, ty=0.0):
        self.sx, self.sy, self.tx, self.ty = sx, sy, tx, ty

    def apply(self, x, y, w, h):
        return (x * self.sx + self.tx, y * self.sy + self.ty, w * self.sx, h * self.sy)

    def compose_group(self, grp_shape) -> "Transform":
        xfrm = grp_shape._element.find("./p:grpSpPr/a:xfrm", NS)
        if xfrm is None:
            return self
        def pair(tag, a, b):
            el = xfrm.find(f"a:{tag}", NS)
            return (int(el.get(a)), int(el.get(b))) if el is not None else None
        off, ext = pair("off", "x", "y"), pair("ext", "cx", "cy")
        ch_off, ch_ext = pair("chOff", "x", "y"), pair("chExt", "cx", "cy")
        if not (off and ext and ch_off and ch_ext):
            return self
        gsx = ext[0] / ch_ext[0] if ch_ext[0] else 1.0
        gsy = ext[1] / ch_ext[1] if ch_ext[1] else 1.0
        gtx = off[0] - ch_off[0] * gsx
        gty = off[1] - ch_off[1] * gsy
        # self ∘ group
        return Transform(self.sx * gsx, self.sy * gsy, self.sx * gtx + self.tx, self.sy * gty + self.ty)


def bbox_of(shape, tf: Transform, sw: int, sh: int):
    """スライドに対する比（0〜1）の外接矩形 [x, y, w, h]。位置を持たない図形はレイアウトから継承するので、なければ None。"""
    try:
        x, y, w, h = shape.left, shape.top, shape.width, shape.height
    except Exception:
        return None
    if x is None or y is None:
        return None
    x, y, w, h = tf.apply(int(x), int(y), int(w or 0), int(h or 0))
    return [round(x / sw, 4), round(y / sh, 4), round(w / sw, 4), round(h / sh, 4)]


def _best_gap(blocks: list[dict], axis: int, scale: float = 1.0):
    """軸 axis（0=x, 1=y）で、図形の影が途切れる帯のうち最も広いもの → (幅, 切る位置)。なければ None。"""
    spans = sorted((b["bbox"][axis], b["bbox"][axis] + b["bbox"][axis + 2]) for b in blocks)
    best = None
    reach = spans[0][1]
    for start, end in spans[1:]:
        gap = (start - reach) * scale
        # 小さな重なり（0.5%）は許して切る。図形の枠がわずかに重なるのはよくある
        if gap >= -0.005 * scale and (best is None or gap > best[0]):
            best = (gap, (reach + start) / 2)
        reach = max(reach, end)
    return best


def xy_cut(blocks: list[dict], aspect: float = 16 / 9, depth: int = 0) -> list[dict]:
    """再帰 XY-cut。上下・左右それぞれで最も広い空白の帯を探し、広い方で切る（同じなら上下を優先）。

    上下を常に先に切ると、2段組みで「左の見出し → 右の見出し → 左の本文 → 右の本文」と交互に読んでしまう。
    切れなければ (top, left) で並べる。
    """
    if len(blocks) <= 1 or depth > 50:
        return blocks
    # 座標はスライドに対する比なので、横長のスライドでは x の比を aspect 倍して実際の幅にそろえて比べる
    gy, gx = _best_gap(blocks, 1), _best_gap(blocks, 0, aspect)
    order = sorted([(g, axis) for g, axis in ((gy, 1), (gx, 0)) if g], key=lambda t: (-t[0][0], -t[1]))
    for (gap, cut), axis in order:
        first = [b for b in blocks if b["bbox"][axis] + b["bbox"][axis + 2] / 2 < cut]
        second = [b for b in blocks if b["bbox"][axis] + b["bbox"][axis + 2] / 2 >= cut]
        if first and second:
            return xy_cut(first, aspect, depth + 1) + xy_cut(second, aspect, depth + 1)
    return sorted(blocks, key=lambda b: (round(b["bbox"][1], 2), b["bbox"][0]))


# ---------------------------------------------------------------- テキスト


_BLOCK_START = re.compile(r"^(\s*)(#{1,6}\s|>|[-+*]\s|\d+[.)]\s)")


def escape_line_start(md: str) -> str:
    """段落の先頭が Markdown の見出し・引用・リストに見える文字なら、記号として残るようにエスケープする。"""
    return _BLOCK_START.sub(lambda m: m.group(1) + "\\" + m.group(2), md, count=1)


def _run_md(text: str, rpr, link: str | None) -> str:
    if not text.strip():
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()) :]
    core = text.strip()
    if rpr is not None:
        if rpr.get("b") in ("1", "true"):
            core = f"**{core}**"
        if rpr.get("i") in ("1", "true"):
            core = f"*{core}*"
    if link:
        core = f"[{core}]({link})"
    return lead + core + trail


def paragraph_info(p_el, part, default_bulleted: bool, counters: dict) -> dict | None:
    """段落1つ → {text, md, level, bullet}。空の段落は None。"""
    ppr = p_el.find("a:pPr", NS)
    level = int(ppr.get("lvl", "0")) if ppr is not None else 0
    plain, md = [], []
    for child in p_el:
        tag = etree.QName(child).localname
        if tag in ("r", "fld"):
            t = child.find("a:t", NS)
            text = t.text if t is not None and t.text else ""
            rpr = child.find("a:rPr", NS)
            link = None
            if rpr is not None:
                h = rpr.find("a:hlinkClick", NS)
                rid = h.get(f"{{{NS['r']}}}id") if h is not None else None
                if rid:
                    try:
                        link = part.rels[rid].target_ref
                    except Exception:
                        link = None
            plain.append(text)
            md.append(_run_md(text, rpr, link))
        elif tag == "br":
            plain.append("\n")
            md.append("<br>")
    text = "".join(plain).strip()
    if not text:
        return None

    bullet = None
    if ppr is not None and ppr.find("a:buNone", NS) is not None:
        bullet = None
    elif ppr is not None and ppr.find("a:buAutoNum", NS) is not None:
        auto = ppr.find("a:buAutoNum", NS)
        start = int(auto.get("startAt", "1"))
        key = (level, auto.get("type"))
        for k in [k for k in counters if k[0] > level]:
            del counters[k]  # 親の番号が進んだら、子の番号は振り直す
        counters[key] = counters.get(key, start - 1) + 1
        bullet = f"{counters[key]}."
    elif ppr is not None and ppr.find("a:buChar", NS) is not None:
        bullet = "-"
    elif default_bulleted or level > 0:
        bullet = "-"
    if not (ppr is not None and ppr.find("a:buAutoNum", NS) is not None):
        # 番号付きの並びが途切れたら、その階層より深い番号を振り直す
        for k in [k for k in counters if k[0] >= level]:
            del counters[k]
    return {"text": text, "md": escape_line_start("".join(md).strip()), "level": level, "bullet": bullet}


def text_frame_paragraphs(shape, default_bulleted: bool) -> list[dict]:
    if not getattr(shape, "has_text_frame", False) or not shape.has_text_frame:
        return []
    paras, counters = [], {}
    for p in shape.text_frame._txBody.findall("a:p", NS):
        info = paragraph_info(p, shape.part, default_bulleted, counters)
        if info:
            paras.append(info)
    return paras


# ---------------------------------------------------------------- 表・グラフ・SmartArt


def table_block(shape) -> dict:
    tbl = shape.table
    n_rows, n_cols = len(tbl.rows), len(tbl.columns)
    rows = [["" for _ in range(n_cols)] for _ in range(n_rows)]
    merged = []
    for r in range(n_rows):
        for c in range(n_cols):
            cell = tbl.cell(r, c)
            if cell.is_spanned:
                continue
            text = "\n".join(par.text for par in cell.text_frame.paragraphs).strip()
            if cell.is_merge_origin:
                # 結合された範囲にも同じ値を入れる。行ごとに読んだとき「実装の担当」が空にならないように
                for rr in range(r, min(r + cell.span_height, n_rows)):
                    for cc in range(c, min(c + cell.span_width, n_cols)):
                        rows[rr][cc] = text
                merged.append([r, c, cell.span_height, cell.span_width])
            else:
                rows[r][c] = text
    try:
        header = bool(tbl.first_row)
    except Exception:
        header = True
    return {"kind": "table", "rows": rows, "header": header, "merged": merged}


def chart_block(shape) -> dict:
    chart = shape.chart
    out = {"kind": "chart", "chart_type": None, "title": None, "categories": [], "series": []}
    try:
        out["chart_type"] = str(chart.chart_type).split(".")[-1].split(" ")[0]
    except Exception:
        pass
    try:
        if chart.has_title and chart.chart_title.has_text_frame:
            out["title"] = chart.chart_title.text_frame.text.strip() or None
    except Exception:
        pass
    try:
        plot = chart.plots[0]
        out["categories"] = [str(c) for c in plot.categories]
    except Exception:
        pass
    for plot in chart.plots:
        for s in plot.series:
            try:
                values = list(s.values)
            except Exception:
                values = []
            out["series"].append({"name": s.name, "values": values})
    return out


def smartart_block(shape) -> dict | None:
    rel_ids = shape._element.find(".//dgm:relIds", NS)
    if rel_ids is None:
        return None
    rid = rel_ids.get(f"{{{NS['r']}}}dm")
    try:
        data_part = shape.part.related_part(rid)
    except Exception:
        return None
    root = etree.fromstring(data_part.blob)
    pts = {}
    doc_id = None
    for pt in root.iterfind(".//dgm:ptLst/dgm:pt", NS):
        ptype = pt.get("type", "node")
        mid = pt.get("modelId")
        if ptype == "doc":
            doc_id = mid
        if ptype in ("node", "asst", "doc"):
            text = "\n".join("".join(t.text or "" for t in p.iterfind(".//a:t", NS)) for p in pt.iterfind("./dgm:t/a:p", NS)).strip()
            pts[mid] = text
    children: dict[str, list[tuple[int, str]]] = {}
    for cxn in root.iterfind(".//dgm:cxnLst/dgm:cxn", NS):
        if cxn.get("type", "parOf") != "parOf":
            continue
        children.setdefault(cxn.get("srcId"), []).append((int(cxn.get("srcOrd", "0")), cxn.get("destId")))
    items: list[dict] = []
    visited: set[str] = set()

    def walk(mid, level):
        for _, child in sorted(children.get(mid, [])):
            if child in visited or child not in pts:
                continue
            visited.add(child)
            if pts[child]:
                items.append({"text": pts[child], "level": level})
            walk(child, level + 1)

    if doc_id:
        walk(doc_id, 0)
    # 接続から辿れなかった点も落とさない
    for mid, text in pts.items():
        if mid != doc_id and mid not in visited and text:
            items.append({"text": text, "level": 0})
    return {"kind": "smartart", "items": items} if items else None


# ---------------------------------------------------------------- 画像


def save_image(shape, images_dir: Path, sw: int, sh: int) -> dict | None:
    try:
        image = shape.image
    except Exception:
        return None
    blob = image.blob
    digest = hashlib.sha1(blob).hexdigest()[:16]
    ext = (image.ext or "bin").lower()
    name = f"{digest}.{ext}"
    path = images_dir / name
    if not path.exists():
        images_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    width_px = height_px = None
    try:
        from PIL import Image

        with Image.open(io.BytesIO(blob)) as im:
            width_px, height_px = im.size
    except Exception:
        pass
    area = (int(shape.width or 0) * int(shape.height or 0)) / (sw * sh) if sw and sh else 0
    alt = shape._element.xpath("./*[1]/p:cNvPr/@descr") if hasattr(shape._element, "xpath") else []
    return {
        "kind": "image",
        "file": f"images/{name}",
        "hash": digest,
        "format": ext,
        "alt": (alt[0].strip() if alt else "") or None,
        "width_px": width_px,
        "height_px": height_px,
        "area_ratio": round(area, 4),
        "vlm_ok": ext in VLM_IMAGE_FORMATS,
        "decorative": area < MIN_IMAGE_AREA_RATIO or (width_px is not None and min(width_px, height_px or 0) < MIN_IMAGE_PX),
    }


# ---------------------------------------------------------------- 図形を歩く


def walk_shapes(shapes, tf: Transform, ctx: dict, out: list[dict]) -> None:
    sw, sh = ctx["sw"], ctx["sh"]
    for shape in shapes:
        try:
            st = shape.shape_type
        except Exception:
            st = None
        if st == MSO_SHAPE_TYPE.GROUP:
            walk_shapes(shape.shapes, tf.compose_group(shape), ctx, out)
            continue
        ph_type = None
        if shape.is_placeholder:
            try:
                ph_type = shape.placeholder_format.type
            except Exception:
                ph_type = None
            if ph_type in SKIP_PLACEHOLDERS:
                continue
        bbox = bbox_of(shape, tf, sw, sh) or [0.0, 1.0, 0.0, 0.0]
        base = {"shape": shape.name, "bbox": bbox}

        block = None
        if getattr(shape, "has_table", False) and shape.has_table:
            block = table_block(shape)
        elif getattr(shape, "has_chart", False) and shape.has_chart:
            block = chart_block(shape)
        elif shape._element.find(f".//a:graphicData[@uri='{DIAGRAM_URI}']", NS) is not None:
            block = smartart_block(shape)
        elif isinstance(shape, Picture):  # 画像のプレースホルダ（PlaceholderPicture）も含む
            block = save_image(shape, ctx["images_dir"], sw, sh)
        elif st in (MSO_SHAPE_TYPE.EMBEDDED_OLE_OBJECT, MSO_SHAPE_TYPE.LINKED_OLE_OBJECT):
            try:
                prog = shape.ole_format.prog_id
            except Exception:
                prog = "OLE"
            block = {"kind": "embedded", "prog_id": prog}

        if block is None:
            paras = text_frame_paragraphs(shape, ph_type in BULLETED_PLACEHOLDERS)
            if paras:
                block = {"kind": "text", "paragraphs": paras, "is_title": ph_type in TITLE_PLACEHOLDERS}
        if block is not None:
            out.append({**base, **block})


def sections_by_slide_id(prs) -> dict[int, str]:
    out = {}
    for sec in prs.part._element.iterfind(".//p14:sectionLst/p14:section", NS):
        for sid in sec.iterfind("./p14:sldIdLst/p14:sldId", NS):
            out[int(sid.get("id"))] = sec.get("name")
    return out


def notes_text(slide) -> str:
    if not slide.has_notes_slide:
        return ""
    tf = slide.notes_slide.notes_text_frame
    return tf.text.strip() if tf is not None else ""


def text_units(slide: dict) -> list[str]:
    """網羅率を測る単位。タイトル・段落・表のセル・グラフの名前・SmartArt の項目。"""
    units = [slide["title"]] if slide.get("title") else []
    for b in slide["blocks"]:
        if b["kind"] == "text":
            units += [p["text"] for p in b["paragraphs"]]
        elif b["kind"] == "table":
            units += [c for row in b["rows"] for c in row if c]
        elif b["kind"] == "chart":
            units += [x for x in [b.get("title")] + b["categories"] + [s["name"] for s in b["series"]] if x]
        elif b["kind"] == "smartart":
            units += [i["text"] for i in b["items"]]
    return [u for u in units if u and u.strip()]


def extract(pptx_path: Path, out_dir: Path) -> dict:
    prs = Presentation(str(pptx_path))
    sw, sh = int(prs.slide_width or Emu(12192000)), int(prs.slide_height or Emu(6858000))
    sections = sections_by_slide_id(prs)
    ctx = {"sw": sw, "sh": sh, "images_dir": out_dir / "images"}
    slides = []
    for idx, slide in enumerate(prs.slides, start=1):
        blocks: list[dict] = []
        walk_shapes(slide.shapes, Transform(), ctx, blocks)
        title_blocks = [b for b in blocks if b.get("is_title")]
        title = " ".join(p["text"] for b in title_blocks for p in b["paragraphs"]).replace("\n", " ").strip()
        body = [b for b in blocks if not b.get("is_title")]
        title_guessed = False
        if not title:
            # タイトルのプレースホルダがない（テキストボックスで題を書いた）スライド:
            # 上 20% にある、1段落・60字以下の文字の箱を題とみなす
            cands = [b for b in body if b["kind"] == "text" and b["bbox"][1] < 0.2 and len(b["paragraphs"]) == 1 and len(b["paragraphs"][0]["text"]) <= 60]
            if cands:
                top = min(cands, key=lambda b: (b["bbox"][1], b["bbox"][0]))
                title, title_guessed = top["paragraphs"][0]["text"].replace("\n", " "), True
                body.remove(top)
        slides.append(
            {
                "index": idx,
                "slide_id": slide.slide_id,
                "hidden": slide._element.get("show") == "0",
                "section": sections.get(slide.slide_id),
                "layout": slide.slide_layout.name,
                "title": title or None,
                "title_guessed": title_guessed,
                "blocks": xy_cut(body, sw / sh),
                "notes": notes_text(slide),
            }
        )

    # 半数以上のスライドに出る同じ画像はロゴとして装飾扱いにする（スライドが3枚以上のときだけ）
    counts = Counter(b["hash"] for s in slides for b in {x["hash"]: x for x in s["blocks"] if x["kind"] == "image"}.values())
    for s in slides:
        for b in s["blocks"]:
            if b["kind"] == "image" and len(slides) >= 3 and counts[b["hash"]] / len(slides) >= REPEATED_IMAGE_RATIO:
                b["decorative"] = True
        s["text_units"] = text_units(s)

    data = {
        "source": {
            "file": pptx_path.name,
            "sha256": sha256_of(pptx_path.read_bytes()),
            "slide_width_emu": sw,
            "slide_height_emu": sh,
            "slide_count": len(slides),
        },
        "slides": slides,
    }
    return data


# ---------------------------------------------------------------- 描画（LibreOffice）


def render_slides(pptx_path: Path, out_dir: Path, slides: list[dict], dpi: int = 110, timeout: int = 300) -> list[str]:
    """スライド全体を PNG にする。失敗しても抽出は続ける（VLM はテキストだけで動く）。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice or not shutil.which("pdftoppm"):
        return ["LibreOffice（soffice）か pdftoppm がないので、スライドの画像は作らない"]
    warnings = []
    renders = out_dir / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "deck.pptx"
        shutil.copy(pptx_path, src)
        # 非表示スライドも PDF に出して、ページ番号とスライド番号を一致させる
        filt = 'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"true"},"ExportNotesPages":{"type":"boolean","value":"false"}}'
        cmd = [soffice, f"-env:UserInstallation=file://{tmp}/lo-profile", "--headless", "--convert-to", filt, "--outdir", str(tmp), str(src)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
        except (subprocess.SubprocessError, OSError) as e:
            return [f"PDF への変換に失敗: {e}"]
        pdf = tmp / "deck.pdf"
        if not pdf.exists():
            return ["PDF への変換に失敗（出力がない）"]
        try:
            subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(tmp / "page")], check=True, capture_output=True, timeout=timeout)
        except (subprocess.SubprocessError, OSError) as e:
            return [f"PNG への変換に失敗: {e}"]
        pages = sorted(tmp.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
        targets = slides
        if len(pages) != len(slides):
            visible = [s for s in slides if not s["hidden"]]
            if len(pages) == len(visible):
                targets = visible
                warnings.append("非表示スライドが PDF に出なかったので、表示スライドだけに画像を割り当てた")
            else:
                return [f"ページ数（{len(pages)}）とスライド数（{len(slides)}）が合わないので、画像は使わない"]
        for page, s in zip(pages, targets):
            name = f"slide-{s['index']:03d}.png"
            shutil.move(str(page), renders / name)
            s["render"] = f"renders/{name}"
    return warnings


# ---------------------------------------------------------------- 決定的な Markdown


def block_to_markdown(b: dict) -> str:
    """図形1つ分の決定的な Markdown。VLM の出力に表・グラフを差し込むときにも使う。"""
    k = b["kind"]
    lines: list[str] = []
    if k == "text":
        prev_bullet = False
        for p in b["paragraphs"]:
            indent = "  " * p["level"]
            if p["bullet"]:
                lines.append(f"{indent}{p['bullet']} {p['md']}")
            else:
                if prev_bullet:
                    lines.append("")  # 空行がないと直前のリスト項目の続きとして読まれる
                lines += [f"{indent}{p['md']}" if p["level"] else p["md"], ""]
            prev_bullet = bool(p["bullet"])
    elif k == "table" and b["rows"]:
        width = max(len(r) for r in b["rows"])
        rows = [r + [""] * (width - len(r)) for r in b["rows"]]
        head = rows[0] if b["header"] else [f"列{i + 1}" for i in range(width)]
        body = rows[1:] if b["header"] else rows
        lines.append("| " + " | ".join(md_escape_cell(c) for c in head) + " |")
        lines.append("|" + "---|" * width)
        lines += ["| " + " | ".join(md_escape_cell(c) for c in r) + " |" for r in body]
    elif k == "chart":
        title = b.get("title") or (b["series"][0]["name"] if len(b["series"]) == 1 else None)
        lines += [f"**グラフ（{b.get('chart_type') or '種類不明'}）" + (f": {title}**" if title else "**"), ""]
        if b["series"]:
            cats = b["categories"] or [str(i + 1) for i in range(max(len(s["values"]) for s in b["series"]))]
            lines.append("| 系列 | " + " | ".join(md_escape_cell(c) for c in cats) + " |")
            lines.append("|" + "---|" * (len(cats) + 1))
            for s in b["series"]:
                vals = ["" if v is None else f"{v:g}" if isinstance(v, float) else str(v) for v in s["values"]]
                lines.append(f"| {md_escape_cell(str(s['name']))} | " + " | ".join(vals) + " |")
    elif k == "smartart":
        lines += [f"{'  ' * it['level']}- {it['text'].replace(chr(10), ' / ')}" for it in b["items"]]
    elif k == "image" and not b["decorative"]:
        lines.append(f"![{b.get('alt') or '画像'}]({b['file']})")
    elif k == "embedded":
        lines.append(f"> 埋め込みオブジェクト（{b['prog_id']}）。中身は抽出していない")
    return "\n".join(lines).strip()


def blocks_to_markdown(blocks: list[dict]) -> str:
    out = "\n\n".join(m for m in (block_to_markdown(b) for b in blocks) if m)
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.strip()


def slide_heading(s: dict) -> str:
    return f"## スライド {s['index']}: {s['title'] or '（タイトルなし）'}"


def notes_markdown(s: dict) -> str:
    if not s.get("notes"):
        return ""
    quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in s["notes"].splitlines())
    return f"### 発表者ノート\n\n{quoted}"


def slide_markdown(s: dict, body: str | None = None) -> str:
    parts = [f"<!-- slide: {s['index']} -->", slide_heading(s)]
    meta = []
    if s.get("section"):
        meta.append(f"セクション: {s['section']}")
    if s.get("hidden"):
        meta.append("非表示スライド")
    if meta:
        parts.append(f"*{' / '.join(meta)}*")
    b = blocks_to_markdown(s["blocks"]) if body is None else body
    if b:
        parts.append(b)
    n = notes_markdown(s)
    if n:
        parts.append(n)
    return "\n\n".join(parts)


def deck_markdown(data: dict, bodies: dict[int, str] | None = None, include_hidden: bool = False) -> str:
    src = data["source"]
    head = f"# {src['file']}\n\n<!-- source-sha256: {src['sha256']} -->"
    parts = [head]
    for s in data["slides"]:
        if s["hidden"] and not include_hidden:
            continue
        parts.append(slide_markdown(s, (bodies or {}).get(s["index"])))
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="pptx からテキスト・画像・構造を抽出する")
    ap.add_argument("pptx", type=Path)
    ap.add_argument("--out", "-o", type=Path, required=True)
    ap.add_argument("--no-render", action="store_true", help="スライド全体の画像を作らない")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--include-hidden", action="store_true", help="非表示スライドも Markdown に入れる")
    args = ap.parse_args(argv)

    if args.pptx.suffix.lower() != ".pptx":
        ap.error(".pptx だけに対応（.ppt は先に LibreOffice などで .pptx に変換する）")
    args.out.mkdir(parents=True, exist_ok=True)
    data = extract(args.pptx, args.out)
    old = args.out / "slides.json"
    if old.exists():
        try:
            old_sha = json.loads(old.read_text(encoding="utf-8"))["source"]["sha256"]
        except Exception:
            old_sha = None
        if old_sha != data["source"]["sha256"]:
            # 別の資料（または更新された資料）。前の資料の Markdown が混ざらないように消す
            shutil.rmtree(args.out / "md", ignore_errors=True)
            shutil.rmtree(args.out / "renders", ignore_errors=True)
            for name in ("deck.md", "vlm_report.json"):
                (args.out / name).unlink(missing_ok=True)
    warnings = [] if args.no_render else render_slides(args.pptx, args.out, data["slides"], args.dpi)
    data["warnings"] = warnings
    data["include_hidden"] = args.include_hidden
    write_json(args.out / "slides.json", data)
    (args.out / "extracted.md").write_text(deck_markdown(data, include_hidden=args.include_hidden), encoding="utf-8")

    n_img = sum(1 for s in data["slides"] for b in s["blocks"] if b["kind"] == "image" and not b["decorative"])
    n_render = sum(1 for s in data["slides"] if s.get("render"))
    print(json.dumps({"slides": len(data["slides"]), "content_images": n_img, "renders": n_render, "warnings": warnings, "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
