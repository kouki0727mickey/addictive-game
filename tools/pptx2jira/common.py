"""各段階で共有する小さな道具: テキストの正規化、網羅率（coverage）の計算、JSONの読み書き。

網羅率は「抽出した原文の各行が、生成したMarkdownにどれだけ残っているか」を測る。
VLM（vLLM）が文字を落とした・言い換えた・数字を作った、を機械的に見つけるための物差し。
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

# Markdown の装飾記号。比較の前に取り除く
_MD_NOISE = re.compile(r"[*_`#>|~\[\]()\-+•●○■□◆◇▶►・※]+")
_SPACE = re.compile(r"\s+")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def strip_md_targets(text: str) -> str:
    """コメント・画像のパス・リンク先URLを消す（リンクの文字は残す）。比較と数字の検査の前に使う。"""
    t = _COMMENT.sub(" ", text)
    t = _IMAGE.sub(r"\1", t)
    return _LINK.sub(r"\1", t)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def normalize(text: str) -> str:
    """比較用の正規化。全角半角（NFKC）、大文字小文字、装飾記号、空白の差を消す。"""
    t = unicodedata.normalize("NFKC", strip_md_targets(text)).lower()
    t = re.sub(r"<br\s*/?>", " ", t)
    t = _MD_NOISE.sub(" ", t)
    return _SPACE.sub("", t)


def numbers_in(text: str) -> set[str]:
    """数字（1,000 や 3.5 を含む）の集合。カンマは取り除いて比べる。"""
    t = unicodedata.normalize("NFKC", text)
    out = set()
    for m in _NUMBER.finditer(t):
        n = m.group(0).replace(",", "")
        if re.fullmatch(r"\d+\.0+", n):
            n = n.split(".")[0]  # グラフの値 12.0 と本文の 12 を同じに扱う
        out.add(n)
    return out


def _contains_fuzzy(needle: str, hay: str, threshold: float) -> bool:
    if not needle:
        return True
    if needle in hay:
        return True
    if len(needle) < 6:
        # 短い断片（"Q3" など）はあいまい一致させると誤検出が多いので、完全一致だけ
        return False
    # needle と同じ長さの窓を hay 上で滑らせ、最良の一致率を見る。
    # 窓は needle の 1/4 ずつずらす（全位置を試すと遅い）。get_matching_blocks で窓の候補を絞る
    sm = SequenceMatcher(None, needle, hay, autojunk=False)
    n = len(needle)
    best = 0.0
    for block in sm.get_matching_blocks():
        if block.size == 0:
            continue
        start = max(0, block.b - block.a)
        for s in (start - n // 4, start, start + n // 4):
            s = max(0, s)
            window = hay[s : s + n + n // 4]
            r = SequenceMatcher(None, needle, window, autojunk=False).ratio()
            if r > best:
                best = r
                if best >= threshold:
                    return True
    return best >= threshold


def coverage(source_units: list[str], generated: str, threshold: float = 0.85) -> tuple[float, list[str]]:
    """原文の単位（行・セル）のうち、生成文に残っている割合と、落ちた単位の一覧を返す。

    重みは文字数。長い行を落とすほど網羅率が大きく下がる。
    """
    hay = normalize(generated)
    total = 0
    kept = 0
    missing: list[str] = []
    seen: set[str] = set()
    for unit in source_units:
        n = normalize(unit)
        if not n or n in seen:
            continue
        seen.add(n)
        total += len(n)
        if _contains_fuzzy(n, hay, threshold):
            kept += len(n)
        else:
            missing.append(unit.strip())
    return (kept / total if total else 1.0), missing


def invented_numbers(source_text: str, generated: str) -> list[str]:
    """生成文にあって原文にない数字。VLMの作り話（桁違い・日付の捏造）を見つける。

    スライド番号の注釈（<!-- slide: 3 -->）と、1桁の数字（見出し番号・箇条書き番号）は除く。
    """
    gen = strip_md_targets(generated)
    src = numbers_in(source_text)
    out = sorted(n for n in numbers_in(gen) - src if len(n.replace(".", "")) >= 2)
    return out


def sha256_of(*parts: bytes | str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8") if isinstance(p, str) else p)
        h.update(b"\0")
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)  # 途中で落ちても壊れたJSONを残さない


def md_escape_cell(text: str) -> str:
    """Markdown の表のセルに入れられる形にする（| と改行）。"""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\r", "").replace("\n", "<br>").strip()
