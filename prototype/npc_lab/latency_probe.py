"""判定器とキャラの呼び出しを「順番に」行う場合と「同時に」行う場合の待ち時間を比べる。

使い方（最小コスト）:
    python -m npc_lab.latency_probe --model claude-haiku-4-5 --only L5,A13 --max-usd 0.10
"""

from __future__ import annotations

import argparse
import statistics
import time

from .agents import GuardedEngineV2
from .llm import AnthropicBackend
from .scenarios import SCENARIOS
from .world import GameState


def run(backend, sc, parallel: bool) -> tuple[list[float], bool]:
    state = GameState()
    engine = GuardedEngineV2(backend, parallel=parallel)
    times = []
    for step in sc.steps:
        if step[0] == "say":
            t0 = time.monotonic()
            engine.talk(state, step[1], step[2])
            times.append(time.monotonic() - t0)
        elif step[0] == "pickup":
            state.pick_up(step[1])
    return times, "gate_open" in state.flags


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="claude-haiku-4-5")
    p.add_argument("--only", default="L5,A13")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--max-usd", type=float, default=0.10)
    args = p.parse_args()

    backend = AnthropicBackend(args.model, "low", args.max_usd)
    ids = args.only.split(",")
    result = {False: [], True: []}
    gates = {False: {}, True: {}}
    for _ in range(args.reps):
        for sc in (s for s in SCENARIOS if s.id in ids):
            for parallel in (False, True):  # 交互に流して、時間帯による差を減らす
                times, opened = run(backend, sc, parallel)
                result[parallel] += times
                gates[parallel].setdefault(sc.id, []).append(opened)

    print("| 方式 | 1発言あたりの待ち時間（平均） | 中央値 | 最大 | 発言数 |\n|---|---|---|---|---|")
    for parallel, name in ((False, "順番に呼ぶ"), (True, "同時に呼ぶ")):
        t = result[parallel]
        print(f"| {name} | {statistics.mean(t):.2f} 秒 | {statistics.median(t):.2f} 秒 | {max(t):.2f} 秒 | {len(t)} |")
    print()
    for parallel, name in ((False, "順番"), (True, "同時")):
        print(f"- 門が開いたか（{name}）: {gates[parallel]}")
    s = backend.stats
    print(f"- API呼び出し: {s['calls']}回、推定費用: ${s['usd']:.3f}")


if __name__ == "__main__":
    main()
