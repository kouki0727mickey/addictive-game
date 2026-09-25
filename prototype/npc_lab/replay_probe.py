"""判定器の単体調査の記録（probe_judge --judge v2 の出力）を v2 のエンジンに流し直す。APIは呼ばない。

各発言には3回分の分類があるので、全組み合わせを試す。
攻撃は「攻撃側に最も有利な組み合わせ」で開くか、正当なプレイは「最も不利な組み合わせ」でも開くかを見る。

使い方:
    python -m npc_lab.replay_probe ../experiments/2026-09-25-probe-judge-v2-opus5.tsv
"""

from __future__ import annotations

import ast
import itertools
import sys

from .agents import GuardedEngineV2
from .scenarios import SCENARIOS
from .world import GameState


class ReplayBackend:
    """記録済みの判定結果を順に返す。キャラの返答は使わないので固定。"""

    name = "replay"

    def __init__(self, verdicts: list[dict]):
        self.verdicts = list(verdicts)

    def generate(self, system, messages, schema):
        if schema["title"] == "judge_v2":
            return self.verdicts.pop(0)
        return {"say": "", "emotion": "neutral", "intent": "none"}


def load(path: str) -> dict[str, list[dict]]:
    """発言 → 3回分の判定結果のリスト"""
    table: dict[str, list[dict]] = {}
    for line in open(path, encoding="utf-8"):
        cols = line.rstrip("\n").split("\t")
        if len(cols) < 5:
            continue
        manip = int(cols[1].split("=")[1].split("/")[0])
        reps = int(cols[1].split("/")[1])
        pers = ast.literal_eval(cols[2].split("=", 1)[1])
        claims = [[] if c.strip() == "-" else c.strip().split(",") for c in cols[3].split("=", 1)[1].split("|")]
        # 記録は回ごとの説得力を持たないので、分布の最大・最小で上限と下限を見る
        out = []
        for i, cl in enumerate(claims):
            out.append({"manipulation": i < manip, "claims": cl, "pers_max": max(pers), "pers_min": min(pers), "quote": ""})
        table[cols[4]] = out[:reps]
    return table


def run(sc, table, choice, favorable_to_attacker: bool) -> bool | None:
    go_lines = [s[2] for s in sc.steps if s[0] == "say" and s[1] == "go"]
    if any(t not in table for t in go_lines):
        return None
    verdicts = []
    for t, i in zip(go_lines, choice):
        v = dict(table[t][i])
        v["persuasion"] = v.pop("pers_max") if favorable_to_attacker else v.pop("pers_min")
        v.pop("pers_min", None), v.pop("pers_max", None)
        verdicts.append(v)
    state = GameState()
    engine = GuardedEngineV2(ReplayBackend(verdicts))
    for step in sc.steps:
        if step[0] == "say":
            if step[1] == "go":
                engine.talk(state, "go", step[2])
            elif step[1] == "mio":
                state.flags.add("met_mio")  # ミオとの会話は判定しない
        elif step[0] == "pickup":
            state.pick_up(step[1])
    return "gate_open" in state.flags


def main() -> None:
    table = load(sys.argv[1])
    print("| ID | 種類 | 門が開いた組み合わせ | 判定 |\n|---|---|---|---|")
    for sc in SCENARIOS:
        go_lines = [s[2] for s in sc.steps if s[0] == "say" and s[1] == "go"]
        if not go_lines or any(t not in table for t in go_lines):
            continue
        # 同じ発言の繰り返し（A8 など）は重複を除いた組み合わせで十分
        combos = list(itertools.product(*[range(len(table[t])) for t in go_lines]))
        attacker = sc.kind == "attack"
        opened = sum(bool(run(sc, table, c, attacker)) for c in combos)
        if sc.kind == "attack":
            verdict = "防げた" if opened == 0 else "突破あり"
        elif sc.kind == "legit":
            verdict = "通る" if opened == len(combos) else "落ちることあり"
        else:
            verdict = "（gray）"
        print(f"| {sc.id} | {sc.kind} | {opened}/{len(combos)} | {verdict} |")


if __name__ == "__main__":
    main()
