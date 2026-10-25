"""テスト用の pptx を作る。抽出で崩れやすい要素を一通り入れる。

- タイトル + 階層つき箇条書き（番号付き・記号なしを含む）
- 2段組み（左右の箱）: 座標で並べると左右が交互になる配置
- グループ図形（子の座標系が親と違う）
- 結合セルを含む表
- 棒グラフ
- 画像（内容の画像と、全スライドに出るロゴ）
- 発表者ノート、非表示スライド、ハイパーリンク、太字
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.oxml.ns import qn
from pptx.util import Inches


def _png(w, h, color, text=""):
    im = Image.new("RGB", (w, h), color)
    if text:
        ImageDraw.Draw(im).text((10, 10), text, fill="white")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    buf.seek(0)
    return buf


def _numbered(paragraph, start=None):
    ppr = paragraph._p.get_or_add_pPr()
    auto = etree.SubElement(ppr, qn("a:buAutoNum"))
    auto.set("type", "arabicPeriod")
    if start:
        auto.set("startAt", str(start))


def _no_bullet(paragraph):
    ppr = paragraph._p.get_or_add_pPr()
    etree.SubElement(ppr, qn("a:buNone"))


def _logo(slide):
    slide.shapes.add_picture(_png(120, 40, "navy", "LOGO"), Inches(12.0), Inches(0.1), Inches(1.0), Inches(0.33))


def build(path: Path) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 1. 表紙
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = "新決済基盤 リニューアル計画"
    s.placeholders[1].text = "2026年度 第3四半期 キックオフ"
    _logo(s)

    # 2. 要件（階層つき箇条書き、番号、太字、リンク）
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "機能要件"
    tf = s.placeholders[1].text_frame
    tf.text = "ユーザー認証をSSOに統一する"
    p = tf.add_paragraph()
    p.text = "対象: 社内管理画面と加盟店ポータル"
    p.level = 1
    p = tf.add_paragraph()
    r = p.add_run()
    r.text = "決済APIのレスポンスを300ms以内にする"
    r.font.bold = True
    p = tf.add_paragraph()
    r = p.add_run()
    r.text = "仕様書"
    r.hyperlink.address = "https://example.com/spec"
    r2 = p.add_run()
    r2.text = " を参照"
    p.level = 1
    for i, t in enumerate(["監査ログを7年保管する", "障害時は5分以内に切り替える"]):
        p = tf.add_paragraph()
        p.text = t
        _numbered(p)
    s.notes_slide.notes_text_frame.text = "SSOはOktaを想定。担当は認証チーム。期限は11月末。"
    _logo(s)

    # 3. 2段組み: 左の箱が上下2つ、右の箱が上下2つ。左を読み切ってから右を読むのが正しい
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "現状と課題"
    for col, (head, body) in enumerate([("現状", "決済処理が夜間バッチで遅い"), ("課題", "リアルタイム化が必要")]):
        left = Inches(0.5 + col * 6.5)
        tb = s.shapes.add_textbox(left, Inches(1.6), Inches(6.0), Inches(0.6))
        tb.text_frame.text = f"{head}（見出し）"
        tb = s.shapes.add_textbox(left, Inches(2.4), Inches(6.0), Inches(2.0))
        tb.text_frame.text = body
        p = tb.text_frame.add_paragraph()
        p.text = f"{head}の詳細メモ"
        _no_bullet(p)
    _logo(s)

    # 4. グループ図形（子の座標系を縮小）と、結合セルのある表
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "体制とスケジュール"
    grp = s.shapes.add_group_shape()
    a = grp.shapes.add_textbox(Inches(0), Inches(0), Inches(4), Inches(1))
    a.text_frame.text = "PM: 山田"
    b = grp.shapes.add_textbox(Inches(0), Inches(1.2), Inches(4), Inches(1))
    b.text_frame.text = "開発: 決済チーム"
    xfrm = grp._element.grpSpPr.find(qn("a:xfrm"))
    # 子の座標系 (0,0)-(4in,2.2in) を、スライド上の (0.5in, 5in) から半分の大きさに置く
    xfrm.find(qn("a:off")).set("x", str(Inches(0.5)))
    xfrm.find(qn("a:off")).set("y", str(Inches(5.0)))
    xfrm.find(qn("a:ext")).set("cx", str(Inches(2)))
    xfrm.find(qn("a:ext")).set("cy", str(Inches(1.1)))
    xfrm.find(qn("a:chOff")).set("x", "0")
    xfrm.find(qn("a:chOff")).set("y", "0")
    xfrm.find(qn("a:chExt")).set("cx", str(Inches(4)))
    xfrm.find(qn("a:chExt")).set("cy", str(Inches(2.2)))
    rows, cols = 4, 3
    tbl = s.shapes.add_table(rows, cols, Inches(0.5), Inches(1.5), Inches(8), Inches(3)).table
    data = [["フェーズ", "期間", "担当"], ["設計", "10月", "決済チーム"], ["実装", "11月〜12月", "決済チーム"], ["移行", "1月", "インフラ"]]
    tbl.cell(1, 2).merge(tbl.cell(2, 2))  # 担当を縦に結合（結合してから文字を入れる。結合は中身を連結するため）
    for r in range(rows):
        for c in range(cols):
            if not tbl.cell(r, c).is_spanned:
                tbl.cell(r, c).text = data[r][c]
    _logo(s)

    # 5. グラフと内容の画像
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "障害件数の推移"
    cd = CategoryChartData()
    cd.categories = ["4月", "5月", "6月"]
    cd.add_series("障害件数", (12, 8, 3))
    s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.5), Inches(1.5), Inches(6), Inches(4), cd)
    pic = s.shapes.add_picture(_png(640, 400, "darkgreen", "architecture"), Inches(7), Inches(1.5), Inches(5.5), Inches(3.4))
    pic._element.nvPicPr.cNvPr.set("descr", "新しいシステム構成図")
    _logo(s)

    # 6. 非表示スライド
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "（没案）旧システム延命"
    s.placeholders[1].text = "延命は採用しない"
    s._element.set("show", "0")

    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(path))
    return path


if __name__ == "__main__":
    print(build(Path(sys.argv[1] if len(sys.argv) > 1 else "sample.pptx")))
