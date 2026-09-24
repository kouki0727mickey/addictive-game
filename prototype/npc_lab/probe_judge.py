"""判定器（P17）の出力を発言ごとに表示する調査用スクリプト。

使い方:
    python -m npc_lab.probe_judge --model claude-opus-5 --reps 3
"""

from __future__ import annotations

import argparse
import collections

from .agents import GuardedEngine
from .llm import AnthropicBackend
from .scenarios import SCENARIOS
from .world import CHARACTERS

TARGETS = {"A5", "A6", "A8", "A9", "A10", "A11", "A12", "L2", "L3"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="claude-opus-5")
    p.add_argument("--effort", default="low")
    p.add_argument("--reps", type=int, default=3)
    args = p.parse_args()

    engine = GuardedEngine(AnthropicBackend(args.model, args.effort))
    for sc in SCENARIOS:
        if sc.id not in TARGETS:
            continue
        seen: list[str] = []
        for step in sc.steps:
            if step[0] != "say" or step[2] in seen:
                continue
            seen.append(step[2])
            vs = [engine._judge(CHARACTERS[step[1]], step[2]) for _ in range(args.reps)]
            manip = sum(v["manipulation"] for v in vs)
            pers = dict(sorted(collections.Counter(v["persuasion"] for v in vs).items()))
            print(f"{sc.id}\tmanipulation={manip}/{args.reps}\tpersuasion={pers}\t{step[2]}", flush=True)


if __name__ == "__main__":
    main()
