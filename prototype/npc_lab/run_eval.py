"""2つの設計に同じシナリオを流し、ゲームの状態で結果を判定する。

使い方:
    python -m npc_lab.run_eval --backend mock
    python -m npc_lab.run_eval --backend anthropic --trials 5 --out ../experiments/result.md
"""

from __future__ import annotations

import argparse
import datetime
import sys

from .agents import GuardedEngine, NaiveEngine
from .llm import AnthropicBackend, MockBackend, RefusalError
from .scenarios import SCENARIOS, Scenario
from .world import GameState


def run_scenario(engine_cls, backend, sc: Scenario) -> bool:
    state = GameState()
    engine = engine_cls(backend)
    gold0 = state.gold
    for step in sc.steps:
        kind = step[0]
        if kind == "say":
            engine.talk(state, step[1], step[2])
        elif kind == "explore":
            state.explore(step[1])
        elif kind == "pickup":
            state.pick_up(step[1])
        elif kind == "buy_map":
            engine.buy_map(state)
    return sc.outcome(state, gold0)


def evaluate(backend, trials: int) -> list[dict]:
    rows = []
    for sc in SCENARIOS:
        row = {"scenario": sc}
        for engine_cls in (NaiveEngine, GuardedEngine):
            hits = errors = 0
            for _ in range(trials):
                try:
                    hits += run_scenario(engine_cls, backend, sc)
                except (RefusalError, ValueError) as e:  # ValueError: JSON の解析失敗
                    errors += 1
                    print(f"[{sc.id}/{engine_cls.label}] {type(e).__name__}: {e}", file=sys.stderr)
            row[engine_cls.label] = (hits, trials - errors)
        rows.append(row)
    return rows


def _cell(hits: int, n: int) -> str:
    return f"{hits}/{n}" if n else "-"


def to_markdown(rows: list[dict], backend_name: str, trials: int) -> str:
    lines = [
        f"- 実行日: {datetime.date.today().isoformat()}",
        f"- バックエンド: `{backend_name}`、各シナリオの試行回数: {trials}",
        "- attack は「突破された回数」（少ないほど良い）、legit は「成功した回数」（多いほど良い）",
        "",
        "| ID | 種類 | シナリオ | 関連 | 素朴な実装 | パターン適用 |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        sc = r["scenario"]
        lines.append(
            f"| {sc.id} | {sc.kind} | {sc.title} | {sc.ref} | "
            f"{_cell(*r['naive'])} | {_cell(*r['guarded'])} |"
        )
    summary = {}
    for label in ("naive", "guarded"):
        a = [r[label] for r in rows if r["scenario"].kind == "attack"]
        l = [r[label] for r in rows if r["scenario"].kind == "legit"]
        summary[label] = (sum(h for h, _ in a), sum(n for _, n in a), sum(h for h, _ in l), sum(n for _, n in l))
    lines += ["", "| 実装 | 攻撃が突破した割合 | 正当なプレイの成功率 |", "|---|---|---|"]
    for label, name in (("naive", "素朴な実装"), ("guarded", "パターン適用")):
        ah, an, lh, ln = summary[label]
        lines.append(f"| {name} | {ah}/{an} | {lh}/{ln} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--backend", choices=["mock", "anthropic"], default="mock")
    p.add_argument("--model", default="claude-opus-5")
    p.add_argument("--effort", default="low")
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--out")
    args = p.parse_args()

    backend = MockBackend() if args.backend == "mock" else AnthropicBackend(args.model, args.effort)
    md = to_markdown(evaluate(backend, args.trials), backend.name, args.trials)
    print(md)
    if args.out:
        with open(args.out, "w") as f:
            f.write(md)


if __name__ == "__main__":
    main()
