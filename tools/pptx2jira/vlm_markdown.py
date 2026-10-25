"""段階2: 抽出結果 + スライド画像 を vLLM（OpenAI 互換 API の視覚言語モデル）に渡して、スライドごとの Markdown にする。

役割分担（精度の要）:
  - 文字の正本は抽出したテキスト（slides.json）。VLM には「この文字をそのまま使う」と指示する
  - VLM が足すのは、画像を見ないと分からないこと: 読む順序・まとまり・矢印や流れ・強調・図や写真の中の文字と意味
  - 出力は機械的に検証する。原文の網羅率（coverage）が閾値に届かなければ、抜けた行を示して1回だけやり直させる。
    それでも届かなければ、抽出結果から作った決定的な Markdown に、VLM の図の説明だけを足したものを使う（fallback）
  - 発表者ノートは VLM に通さず、原文のまま後ろに付ける（ノートは要件・担当・期限が書かれやすく、言い換えさせたくない）

出力（抽出と同じディレクトリ）:
  md/slide-NNN.md  スライドごとの本文
  deck.md          全スライドをまとめた Markdown（段階3の入力）
  vlm_report.json  スライドごとの網羅率・抜け・作られた数字・状態
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import coverage, invented_numbers, read_json, sha256_of, write_json  # noqa: E402
from extract import block_to_markdown, blocks_to_markdown, deck_markdown  # noqa: E402

PROMPT_VERSION = "v5"

SYSTEM_PROMPT = """あなたはプレゼン資料を Markdown に起こす担当です。入力は1枚のスライドについて、
(1) 抽出済みの原文（JSON。PowerPoint のファイルから機械的に取り出した文字で、文字そのものは正確）
(2) スライド全体の画像（あれば）
(3) スライドに埋め込まれた画像（あれば。IMG-1, IMG-2 … の名前つき）
です。

守ること:
1. 原文（JSON）の文字は、一字一句そのまま使う。要約・言い換え・翻訳・省略をしない。数字・日付・固有名詞を変えない。
2. スライド画像を見て、人が読む順序とまとまりで並べる。見出し・箇条書きの階層を Markdown で表す。
   表（id が TABLE-n）とグラフ（id が CHART-n）は、中身を書かずに、置きたい位置に {{TABLE-1}} のような行を1行だけ置く。
   こちらで原文から正確な表に差し替える。グラフから読み取れる傾向は「> 図: 」で説明してよい。
3. 図形と矢印で描かれた流れ・関係（例: A → B → C、親子関係）は、画像から読み取って箇条書きか「A → B」の形で書く。
4. 埋め込み画像は1枚ずつ「> 図（IMG-1）: 」のように名前を付けた引用ブロックで説明する。
   スライド画像でしか見えない図形の図・写真は「> 図: 」で始まる引用ブロックで説明する。
   図の中に読める文字があれば、その文字を書き写す（原文の JSON にない文字は、この図の説明の中にだけ書く）。
5. 画像からはっきり読めない文字は推測で埋めず、【要確認】と書く。
6. 原文にも画像にもないこと（解釈・提案・補足）を書かない。
7. 出力は本文の Markdown だけ。スライドのタイトル見出しは付けない（こちらで付ける）。前置き・後書き・コードフェンスは付けない。
   見出しが必要なら ### 以下を使う。"""

RETRY_PROMPT = """前の出力には次の問題があります。原文の文字をそのまま使い、直した本文の Markdown 全体を出し直してください。
{problems}"""


def retry_message(rep: dict) -> str:
    problems = []
    if rep["missing"]:
        problems.append("原文の次の行が含まれていません。すべて含めてください:\n" + "\n".join(f"- {m}" for m in rep["missing"][:40]))
    if rep.get("missing_figures"):
        problems.append("次の画像の説明がありません。それぞれ「> 図（IMG-n）: 」で説明してください: " + ", ".join(rep["missing_figures"]))
    if rep["invented_numbers"]:
        problems.append("原文にない数字が本文にあります（図の説明の外）。原文の数字だけを使ってください: " + ", ".join(rep["invented_numbers"]))
    return RETRY_PROMPT.format(problems="\n\n".join(problems))


# ---------------------------------------------------------------- 入力を組み立てる


def compact_source(slide: dict) -> dict:
    """VLM に渡す原文。座標などの雑音を除き、文字と構造だけにする。"""
    blocks = []
    img_no = tbl_no = chart_no = 0
    for b in slide["blocks"]:
        k = b["kind"]
        if k == "text":
            blocks.append({"type": "text", "paragraphs": [{"level": p["level"], "bullet": p["bullet"], "text": p["md"]} for p in b["paragraphs"]]})
        elif k == "table":
            tbl_no += 1
            blocks.append({"type": "table", "id": f"TABLE-{tbl_no}", "header_row": b["header"], "rows": b["rows"]})
        elif k == "chart":
            chart_no += 1
            blocks.append({"type": "chart", "id": f"CHART-{chart_no}", "chart_type": b["chart_type"], "title": b["title"], "categories": b["categories"], "series": b["series"]})
        elif k == "smartart":
            blocks.append({"type": "diagram", "items": b["items"]})
        elif k == "image" and not b["decorative"]:
            img_no += 1
            blocks.append({"type": "image", "name": f"IMG-{img_no}", "alt": b.get("alt")})
        elif k == "embedded":
            blocks.append({"type": "embedded_object", "prog_id": b["prog_id"]})
    return {"title": slide.get("title"), "blocks": blocks}


def image_data_url(path: Path, max_side: int) -> str | None:
    """VLM に送れる形（PNG/JPEG、長辺 max_side 以下）にする。開けない形式（EMF/WMF など）は None。"""
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.load()
            if im.mode not in ("RGB", "L"):
                bg = Image.new("RGB", im.size, "white")
                im = im.convert("RGBA")
                bg.paste(im, mask=im.split()[-1])
                im = bg
            scale = max_side / max(im.size)
            if scale < 1:
                im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))))
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
    except Exception:
        return None
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def build_messages(slide: dict, root: Path, max_images: int, max_side: int, use_render: bool) -> tuple[list[dict], list[str], list[str]]:
    """(messages, 注意書き, 送った埋め込み画像の名前)"""
    notes = []
    sent: list[str] = []
    content: list[dict] = [{"type": "text", "text": "原文（JSON）:\n" + json.dumps(compact_source(slide), ensure_ascii=False)}]
    if use_render and slide.get("render"):
        url = image_data_url(root / slide["render"], max_side)
        if url:
            content += [{"type": "text", "text": "スライド全体の画像:"}, {"type": "image_url", "image_url": {"url": url}}]
    imgs = [b for b in slide["blocks"] if b["kind"] == "image" and not b["decorative"]]
    # 大きい画像から送る（情報量が多い）。上限を超えた分はスライド全体の画像で見る
    ranked = sorted(enumerate(imgs, start=1), key=lambda t: -t[1]["area_ratio"])
    for no, b in ranked[:max_images]:
        url = image_data_url(root / b["file"], max_side)
        if url:
            content += [{"type": "text", "text": f"IMG-{no}:"}, {"type": "image_url", "image_url": {"url": url}}]
            sent.append(f"IMG-{no}")
        else:
            notes.append(f"IMG-{no}（{b['format']}）は VLM に送れない形式なので、スライド全体の画像だけで見る")
    if len(ranked) > max_images:
        notes.append(f"埋め込み画像 {len(ranked)} 枚のうち {max_images} 枚だけ送った")
    content.append({"type": "text", "text": "このスライドの本文を Markdown にしてください。"})
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}], notes, sorted(sent)


# ---------------------------------------------------------------- 出力を整える・検証する

_THINK = re.compile(r"<think>.*?</think>", re.S)
_FENCE = re.compile(r"^\s*```(?:markdown|md)?\s*\n(.*?)\n```\s*$", re.S)


def clean_output(text: str, title: str | None) -> str:
    t = _THINK.sub("", text or "").strip()
    m = _FENCE.match(t)
    if m:
        t = m.group(1).strip()
    lines = t.splitlines()
    # 先頭にタイトルの見出しを付けてきたら外す（見出しはこちらで付ける）
    if lines and title and re.match(r"^#{1,6}\s", lines[0]) and title.replace(" ", "") in lines[0].replace(" ", ""):
        lines = lines[1:]
    out = []
    for line in lines:
        # # と ## はスライド見出しより上の階層になるので、### に下げる
        m = re.match(r"^(#{1,2})(\s.*)$", line)
        out.append("###" + m.group(2) if m else line)
    return "\n".join(out).strip()


_SLOT = re.compile(r"^\s*\{\{\s*((?:TABLE|CHART)-\d+)\s*\}\}\s*$", re.M)


def fill_slots(slide: dict, md: str) -> str:
    """{{TABLE-n}} / {{CHART-n}} を、抽出した正確な表に差し替える。VLM が置き忘れた表は末尾に足す。"""
    exact = {}
    t = c = 0
    for b in slide["blocks"]:
        if b["kind"] == "table":
            t += 1
            exact[f"TABLE-{t}"] = block_to_markdown(b)
        elif b["kind"] == "chart":
            c += 1
            exact[f"CHART-{c}"] = block_to_markdown(b)
    used = set()

    def sub(m):
        sid = m.group(1)
        if sid in exact and sid not in used:
            used.add(sid)
            return "\n" + exact[sid] + "\n"
        return ""  # 存在しない id・2回目の同じ id は消す

    out = _SLOT.sub(sub, md)
    rest = [exact[k] for k in exact if k not in used]
    if rest:
        out += "\n\n" + "\n\n".join(rest)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def figure_lines(md: str) -> str:
    """VLM の出力から「> 図: 」の引用ブロックだけを抜き出す（fallback で使う）。"""
    keep, inside = [], False
    for line in md.splitlines():
        if line.startswith("> 図"):
            inside = True
        elif not line.startswith(">"):
            inside = False
        if inside:
            keep.append(line)
    return "\n".join(keep)


def body_units(slide: dict) -> list[str]:
    """本文で網羅すべき単位。タイトルは見出しとしてこちらで付けるので除く。"""
    title = slide.get("title")
    units = list(slide["text_units"])
    if title and units and units[0] == title:
        units = units[1:]
    return units


def evaluate(slide: dict, md: str, min_coverage: float, sent_images: list[str] | None = None) -> dict:
    cov, missing = coverage(body_units(slide), md)
    # 送った埋め込み画像には、それぞれ説明が要る（網羅率は文字しか測らないので、図の説明の欠落は別に見る）
    no_figure = [name for name in (sent_images or []) if not re.search(rf"^>\s*図[（(]{re.escape(name)}[）)]", md, re.M)]
    src = "\n".join(slide["text_units"]) + "\n" + json.dumps(compact_source(slide), ensure_ascii=False)
    body_wo_figures = "\n".join(line for line in md.splitlines() if not line.startswith(">"))
    # 図の説明の外に、原文にない数字が出たら作り話の疑い（図の中の文字は原文にないことがあるので除く）
    invented = invented_numbers(src, body_wo_figures)
    return {
        "coverage": round(cov, 4),
        "missing": missing,
        "invented_numbers": invented,
        "missing_figures": no_figure,
        "ok": cov >= min_coverage and not invented and not no_figure,
    }


# ---------------------------------------------------------------- vLLM を呼ぶ


class VLMClient:
    def __init__(self, base_url: str, model: str, api_key: str, max_tokens: int, timeout: int, extra_body: dict):
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra_body = extra_body

    def chat(self, messages: list[dict]) -> tuple[str, dict]:
        body = {"model": self.model, "messages": messages, "temperature": 0, "max_tokens": self.max_tokens, **self.extra_body}
        delay = 2
        for attempt in range(5):
            try:
                r = requests.post(self.url, headers=self.headers, json=body, timeout=self.timeout)
            except requests.RequestException as e:
                err = f"接続エラー: {type(e).__name__}"
            else:
                if r.status_code == 200:
                    data = r.json()
                    choice = data["choices"][0]
                    if choice.get("finish_reason") == "length":
                        raise RuntimeError("max_tokens に達して出力が途中で切れた（--max-tokens を上げる）")
                    return choice["message"].get("content") or "", data.get("usage") or {}
                if r.status_code not in (408, 429, 500, 502, 503, 504):
                    raise RuntimeError(f"vLLM が {r.status_code} を返した: {r.text[:300]}")
                err = f"HTTP {r.status_code}"
            if attempt < 4:
                time.sleep(delay)
                delay *= 2
        raise RuntimeError(f"vLLM の呼び出しに5回失敗した（最後: {err}）")


def process_slide(slide: dict, root: Path, client: VLMClient, args) -> dict:
    messages, notes, sent = build_messages(slide, root, args.max_images, args.image_max_side, not args.no_render_image)
    has_visual = any(c["type"] == "image_url" for c in messages[1]["content"])
    deterministic = blocks_to_markdown(slide["blocks"])
    if not has_visual:
        # 見る画像がなければ VLM の出番はない。抽出結果をそのまま使う（速く、文字は正確）
        rep = evaluate(slide, deterministic, args.min_coverage)
        return {"index": slide["index"], "status": "text_only", "body": deterministic, "notes": notes, **rep}

    cache_key = sha256_of(PROMPT_VERSION, client.model, json.dumps(messages, ensure_ascii=False), str(args.min_coverage))
    cache_file = root / ".cache" / "vlm" / f"{cache_key}.json"
    if cache_file.exists() and not args.no_cache:
        return read_json(cache_file)

    attempts = []
    t0 = time.time()
    text, usage = client.chat(messages)
    body = fill_slots(slide, clean_output(text, slide.get("title")))
    rep = evaluate(slide, body, args.min_coverage, sent)
    attempts.append((rep["coverage"], body, rep, usage))
    tries = 0
    while not rep["ok"] and tries < args.quality_retries:
        tries += 1
        retry = messages + [{"role": "assistant", "content": text}, {"role": "user", "content": retry_message(rep)}]
        text, usage = client.chat(retry)
        body = fill_slots(slide, clean_output(text, slide.get("title")))
        rep = evaluate(slide, body, args.min_coverage, sent)
        attempts.append((rep["coverage"], body, rep, usage))

    # 合格したものを優先し、その中で網羅率の高いもの
    best_cov, best_body, best_rep, _ = max(attempts, key=lambda a: (a[2]["ok"], a[0]))
    status = "vlm" if len(attempts) == 1 else "vlm_retry"
    if not best_rep["ok"]:
        # 文字を落とす出力は使わない。抽出結果の本文に、VLM の図の説明だけを足す
        # 図の説明はどの試行のものでも使う（説明があった試行を優先）
        figs = max((figure_lines(a[1]) for a in attempts), key=len)
        best_body = deterministic + ("\n\n" + figs if figs else "")
        best_rep = evaluate(slide, best_body, args.min_coverage, sent)
        status = "fallback"
    result = {
        "index": slide["index"],
        "status": status,
        "body": best_body,
        "notes": notes,
        "attempts": len(attempts),
        "attempt_coverages": [a[0] for a in attempts],
        "seconds": round(time.time() - t0, 1),
        "usage": [a[3] for a in attempts],
        **best_rep,
    }
    write_json(cache_file, result)
    return result


def write_deck(root: Path, data: dict, include_hidden: bool) -> None:
    """md/ の各スライドから deck.md を作る。md/ にないスライド（--only で外したもの）は抽出結果を使う。"""
    bodies = {}
    for s in data["slides"]:
        f = root / "md" / f"slide-{s['index']:03d}.md"
        if f.exists():
            bodies[s["index"]] = f.read_text(encoding="utf-8").strip()
    (root / "deck.md").write_text(deck_markdown(data, bodies, include_hidden=include_hidden), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="抽出結果を vLLM で Markdown にする")
    ap.add_argument("workdir", type=Path, help="extract.py の --out")
    ap.add_argument("--base-url", default=os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1"))
    ap.add_argument("--model", default=os.environ.get("VLLM_MODEL"), help="vLLM で動かしているモデル名（例: Qwen/Qwen2.5-VL-7B-Instruct）")
    ap.add_argument("--api-key-env", default="VLLM_API_KEY", help="API キーを読む環境変数の名前（値は表示しない）")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--min-coverage", type=float, default=0.95, help="原文の網羅率がこれ未満ならやり直し・fallback")
    ap.add_argument("--quality-retries", type=int, default=1)
    ap.add_argument("--max-images", type=int, default=3, help="1枚のスライドで送る埋め込み画像の上限（vLLM の --limit-mm-per-prompt に合わせる）")
    ap.add_argument("--image-max-side", type=int, default=1600)
    ap.add_argument("--no-render-image", action="store_true", help="スライド全体の画像を送らない")
    ap.add_argument("--extra-body", default="{}", help='vLLM に追加で渡す JSON（例: {"chat_template_kwargs":{"enable_thinking":false}}）')
    ap.add_argument("--only", default="", help="処理するスライド番号（例: 2,5-7）")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="vLLM を呼ばず、呼び出し回数と送る画像の数だけ出す")
    ap.add_argument("--rebuild-deck", action="store_true", help="vLLM を呼ばず、md/ の各スライド（手で直したもの）から deck.md だけ作り直す")
    args = ap.parse_args(argv)

    root = args.workdir
    data = read_json(root / "slides.json")
    include_hidden = data.get("include_hidden", False)
    targets = [s for s in data["slides"] if include_hidden or not s["hidden"]]
    if args.only:
        wanted = set()
        for part in args.only.split(","):
            a, _, b = part.partition("-")
            wanted.update(range(int(a), int(b or a) + 1))
        targets = [s for s in targets if s["index"] in wanted]

    if args.rebuild_deck:
        write_deck(root, data, include_hidden)
        print(json.dumps({"deck": str(root / "deck.md")}, ensure_ascii=False))
        return

    if args.dry_run:
        plan = []
        for s in targets:
            msgs, notes, _ = build_messages(s, root, args.max_images, args.image_max_side, not args.no_render_image)
            n_img = sum(1 for c in msgs[1]["content"] if c["type"] == "image_url")
            plan.append({"slide": s["index"], "images": n_img, "calls": f"1〜{1 + args.quality_retries}" if n_img else "0（text_only）", "notes": notes})
        print(json.dumps({"slides": len(plan), "plan": plan}, ensure_ascii=False, indent=1))
        return
    if not args.model:
        ap.error("--model か環境変数 VLLM_MODEL でモデル名を指定する")

    client = VLMClient(args.base_url, args.model, os.environ.get(args.api_key_env, "EMPTY"), args.max_tokens, args.timeout, json.loads(args.extra_body))
    results: dict[int, dict] = {}
    errors: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futs = {pool.submit(process_slide, s, root, client, args): s for s in targets}
        for f in as_completed(futs):
            s = futs[f]
            try:
                results[s["index"]] = f.result()
            except Exception as e:  # 1枚の失敗で全体を止めない。そのスライドは抽出結果で埋める
                errors[s["index"]] = str(e)
                body = blocks_to_markdown(s["blocks"])
                results[s["index"]] = {"index": s["index"], "status": "error_fallback", "body": body, "error": str(e), **evaluate(s, body, args.min_coverage)}

    md_dir = root / "md"
    md_dir.mkdir(exist_ok=True)
    for idx, r in results.items():
        (md_dir / f"slide-{idx:03d}.md").write_text(r["body"] + "\n", encoding="utf-8")
    write_deck(root, data, include_hidden)

    report_path = root / "vlm_report.json"
    old = read_json(report_path) if report_path.exists() else {"slides": {}}
    old["slides"].update({str(k): {kk: vv for kk, vv in v.items() if kk != "body"} for k, v in results.items()})
    old.update({"model": args.model, "prompt_version": PROMPT_VERSION, "min_coverage": args.min_coverage})
    write_json(report_path, old)

    statuses = {}
    for r in results.values():
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    low = sorted((r["index"], r["coverage"]) for r in results.values() if r["coverage"] < args.min_coverage)
    invented = {r["index"]: r["invented_numbers"] for r in results.values() if r.get("invented_numbers")}
    print(json.dumps({"slides": len(results), "status": statuses, "below_min_coverage": low, "invented_numbers": invented, "errors": errors, "deck": str(root / "deck.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
