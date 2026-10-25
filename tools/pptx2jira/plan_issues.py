"""段階3: deck.md から Jira 課題の計画（issues.json）を Claude API で作る。

Claude Code のスキル（/pptx-to-jira）から使うときは、この段階は Claude Code 自身が
prompts/plan_issues.md に従って issues.json を書くので、このスクリプトは要らない（API 費用もかからない）。
このスクリプトは、CI や大量の資料をまとめて処理するときのためのもの。

- 出力は構造化出力（output_config.format の JSON スキーマ）で受け取り、型が崩れないようにする
- 指示（prompts/plan_issues.md）は system に置いてキャッシュする。資料を何本も流すとき 2 本目から安くなる
- 呼ぶ前に費用を見積もり、--max-usd を超えるなら呼ばない。--dry-run は見積もりだけ
- --review-pass を付けると、2回目の呼び出しで「資料と課題案を突き合わせて直す」。費用は約2倍
- 作った後に issues_schema.lint で検査し、結果を一緒に出す
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_json  # noqa: E402
from issues_schema import PLAN_SCHEMA, autofix, lint  # noqa: E402

HERE = Path(__file__).resolve().parent
SYSTEM_PROMPT = (HERE / "prompts" / "plan_issues.md").read_text(encoding="utf-8")

# 1M トークンあたりのドル（入力, 出力）。見積もりと上限の判定に使う（2026-10 時点の公開価格）
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1.0, 5.0),
}
# server-side fallback（拒否されたときに別モデルで続ける）を受け付けるモデル
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-opus-5", "claude-fable-5-1"}

REVIEW_PROMPT = """次は、上の資料から作った Jira 課題の案です。資料と1件ずつ突き合わせて直した版を、同じスキーマで出してください。

確かめること:
- 資料にある実行すべき事項の取りこぼし（特に表の行、発表者ノートの担当・期限）
- 資料にない作業・数値・日付・担当の混入（あれば消すか open_questions に移す）
- 根拠の引用（evidence）が資料の文と一字一句一致しているか
- 重複する課題、粒度が大きすぎる・小さすぎる課題、type の誤り
- 期限・優先度・担当を推測で埋めていないか（推測なら inferred_fields に入れる）

直した点は review_notes に1行ずつ書く（直す点がなければ空の配列）。

課題の案:
"""


def price_of(model: str) -> tuple[float, float]:
    for k, v in PRICES.items():
        if model.startswith(k):
            return v
    return PRICES["claude-opus-5-5"]  # 不明なモデルは高めに見積もる


def estimate_usd(model: str, in_tok: int, out_tok: int, cache_read: int = 0) -> float:
    pin, pout = price_of(model)
    return (in_tok * pin + cache_read * pin * 0.1 + out_tok * pout) / 1_000_000


def request_kwargs(model: str, deck_md: str, extra_user: str | None, max_tokens: int, effort: str) -> dict:
    # 資料は独立したブロックにしてキャッシュする。--review-pass の2回目は資料の部分がキャッシュから読まれる
    content = [
        {"type": "text", "text": f"<deck>\n{deck_md}\n</deck>", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "上の資料から Jira 課題の計画を作ってください。" + ("\n\n" + extra_user if extra_user else "")},
    ]
    messages = [{"role": "user", "content": content}]
    kw = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        "messages": messages,
        "output_config": {"format": {"type": "json_schema", "schema": PLAN_SCHEMA}},
    }
    if not model.startswith("claude-haiku-4-5"):
        # Haiku 4.5 は effort を受け付けない。それ以外は思考は adaptive（既定）で、深さを effort で決める
        kw["output_config"]["effort"] = effort
    if model in FALLBACK_MODELS:
        kw["betas"] = ["server-side-fallback-2026-07-01"]
        kw["fallbacks"] = "default"
    return kw


def count_input_tokens(client, kw: dict) -> int:
    ct = {k: v for k, v in kw.items() if k in ("model", "system", "messages", "output_config")}
    try:
        return client.beta.messages.count_tokens(**ct).input_tokens
    except Exception:
        # 数えられない（キーなし・ネットワークなし）ときは、日本語を1字≒1トークンとして多めに見積もる
        return len(json.dumps(kw["messages"], ensure_ascii=False)) + len(SYSTEM_PROMPT)


def call_claude(client, kw: dict) -> tuple[dict, dict]:
    import anthropic

    try:
        with client.beta.messages.stream(**kw) as stream:
            msg = stream.get_final_message()
    except anthropic.BadRequestError as e:
        raise SystemExit(f"リクエストが拒否された（400）: {e.message}")
    except anthropic.AuthenticationError:
        raise SystemExit("認証に失敗した。ANTHROPIC_API_KEY か `ant auth login` を確かめる（キーの値は表示しない）")
    except anthropic.RateLimitError:
        raise SystemExit("レート制限に達した。時間をおいて再実行する")
    except anthropic.APIConnectionError as e:
        raise SystemExit(f"API に接続できない: {e}")
    if msg.stop_reason == "refusal":
        raise SystemExit(f"モデルが応答を拒否した（{getattr(msg, 'stop_details', None)}）")
    if msg.stop_reason == "max_tokens":
        raise SystemExit("出力が max_tokens で切れた。--max-tokens を上げるか、資料を分けて流す")
    text = next(b.text for b in msg.content if b.type == "text")
    u = msg.usage
    usage = {
        "model": msg.model,
        "input_tokens": u.input_tokens,
        "output_tokens": u.output_tokens,
        "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
        "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
    }
    return json.loads(text), usage


def main(argv=None):
    ap = argparse.ArgumentParser(description="deck.md から Jira 課題の計画（issues.json）を Claude で作る")
    ap.add_argument("deck", type=Path, help="vlm_markdown.py が作った deck.md（または extracted.md）")
    ap.add_argument("--project-key", required=True)
    ap.add_argument("--out", "-o", type=Path, help="既定: deck.md と同じ場所の issues.json")
    ap.add_argument("--model", default="claude-opus-5-5", help="試すときは claude-haiku-4-5 から（リポジトリの費用方針）")
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--max-tokens", type=int, default=64000)
    ap.add_argument("--max-usd", type=float, default=1.0, help="見積もりがこの額を超えたら呼ばない（既定 1 ドル）")
    ap.add_argument("--review-pass", action="store_true", help="2回目の呼び出しで資料と突き合わせて直す（費用は約2倍）")
    ap.add_argument("--dry-run", action="store_true", help="API を呼ばず、トークン数と費用の見積もりだけ出す")
    args = ap.parse_args(argv)

    deck_md = args.deck.read_text(encoding="utf-8")
    out = args.out or args.deck.with_name("issues.json")
    kw = request_kwargs(args.model, deck_md, None, args.max_tokens, args.effort)

    try:
        import anthropic

        client = anthropic.Anthropic()
    except Exception as e:  # SDK がない・認証情報がない
        client = None
        if not args.dry_run:
            raise SystemExit(f"Anthropic SDK を使えない: {e}（pip install anthropic、ANTHROPIC_API_KEY か `ant auth login`）")

    in_tok = count_input_tokens(client, kw) if client else len(deck_md) + len(SYSTEM_PROMPT)
    # 出力は入力の半分程度（上限 max_tokens）と見積もる。思考のトークンも出力に数えられるので多めに
    out_guess = min(args.max_tokens, max(4000, in_tok // 2))
    calls = 2 if args.review_pass else 1
    est = estimate_usd(args.model, in_tok, out_guess) * calls
    plan_info = {"model": args.model, "input_tokens": in_tok, "output_tokens_guess": out_guess, "calls": calls, "estimated_usd": round(est, 4), "max_usd": args.max_usd}
    if args.dry_run:
        print(json.dumps(plan_info, ensure_ascii=False))
        return 0
    if est > args.max_usd:
        raise SystemExit(f"見積もり {est:.3f} ドルが上限 {args.max_usd} ドルを超える。--max-usd を上げるか、安いモデルで試す: {plan_info}")

    plan, usage = call_claude(client, kw)
    usages = [usage]
    if args.review_pass:
        kw2 = request_kwargs(args.model, deck_md, REVIEW_PROMPT + json.dumps(plan, ensure_ascii=False), args.max_tokens, args.effort)
        plan, usage2 = call_claude(client, kw2)
        usages.append(usage2)
    spent = sum(estimate_usd(u["model"], u["input_tokens"] + u["cache_creation_input_tokens"], u["output_tokens"], u["cache_read_input_tokens"]) for u in usages)

    fixes = autofix(plan)
    result = lint(plan, deck_md)
    src = {}
    for line in deck_md.splitlines()[:5]:
        if line.startswith("<!-- source-sha256:"):
            src["sha256"] = line.split(":", 1)[1].strip(" ->")
        if line.startswith("# "):
            src["file"] = line[2:].strip()
    write_json(out, {"version": 1, "source": src, "project_key": args.project_key, "generated_by": {"tool": "plan_issues.py", "model": args.model, "usage": usages, "usd": round(spent, 4)}, "plan": plan})
    print(json.dumps({"out": str(out), "usd": round(spent, 4), "fixes": fixes, **result}, ensure_ascii=False, indent=1))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
