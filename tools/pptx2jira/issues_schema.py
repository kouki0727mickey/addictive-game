"""段階3と4の間の契約: issues.json のスキーマと、登録前の検査（lint）。

スキーマは Claude の構造化出力（output_config.format）にもそのまま渡すので、
使う機能を絞っている（null は使わず空文字、すべての object に additionalProperties: false と全項目 required）。

検査（lint）は「Jira に入れる前に人が見るべきもの」を機械的に洗い出す:
  - 根拠の引用（evidence）が、出典のスライドに本当にあるか（作り話の検出）
  - 出典スライド・依存先の ref が存在するか、依存が循環していないか
  - 期限が資料の数字と合っているか、推測なら inferred_fields に載っているか
  - Jira の制約（要約 255 字・改行なし、ラベルに空白なし）
  - どの課題にも使われず、除外理由もないスライド（取りこぼし）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import coverage, invented_numbers, normalize, numbers_in, read_json  # noqa: E402

PRIORITIES = ["", "Highest", "High", "Medium", "Low", "Lowest"]
_STR = {"type": "string"}
_STRS = {"type": "array", "items": {"type": "string"}}
_INTS = {"type": "array", "items": {"type": "integer"}}


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


SUBTASK = _obj({"ref": _STR, "summary": _STR, "description": _STR, "source_slides": _INTS, "evidence": _STRS})
ISSUE = _obj(
    {
        "ref": _STR,
        "type": {"type": "string", "enum": ["story", "task", "bug"]},
        "summary": _STR,
        "description": _STR,
        "acceptance_criteria": _STRS,
        "priority": {"type": "string", "enum": PRIORITIES},
        "due_date": _STR,
        "assignee_hint": _STR,
        "labels": _STRS,
        "source_slides": _INTS,
        "evidence": _STRS,
        "depends_on": _STRS,
        "inferred_fields": _STRS,
        "subtasks": {"type": "array", "items": SUBTASK},
    }
)
EPIC = _obj({"ref": _STR, "summary": _STR, "description": _STR, "labels": _STRS, "source_slides": _INTS, "issues": {"type": "array", "items": ISSUE}})
PLAN_SCHEMA = _obj(
    {
        "epics": {"type": "array", "items": EPIC},
        "unassigned_issues": {"type": "array", "items": ISSUE},
        "open_questions": {"type": "array", "items": _obj({"question": _STR, "source_slides": _INTS})},
        "skipped_slides": {"type": "array", "items": _obj({"slide": {"type": "integer"}, "reason": _STR})},
        "review_notes": _STRS,
    }
)


# ---------------------------------------------------------------- deck.md を読む


def slides_from_deck(deck_md: str) -> dict[int, str]:
    """deck.md をスライド番号 → そのスライドの Markdown に分ける。"""
    parts = re.split(r"<!-- slide: (\d+) -->", deck_md)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        out[int(parts[i])] = parts[i + 1]
    return out


def all_issues(plan: dict):
    """(エピックの ref または None, 課題) を順に返す。"""
    for e in plan.get("epics", []):
        for it in e.get("issues", []):
            yield e["ref"], it
    for it in plan.get("unassigned_issues", []):
        yield None, it


def all_refs(plan: dict) -> list[str]:
    refs = [e["ref"] for e in plan.get("epics", [])]
    for _, it in all_issues(plan):
        refs.append(it["ref"])
        refs += [st["ref"] for st in it.get("subtasks", [])]
    return refs


# ---------------------------------------------------------------- 自動で直せるもの


def sanitize_label(label: str) -> str:
    return re.sub(r"[^\w.-]+", "-", label.strip()).strip("-")[:255]


def autofix(plan: dict) -> list[str]:
    """意味を変えない直しだけをする（ラベルの空白・要約の改行と前後の空白・重複ラベル）。"""
    fixes = []

    def fix_item(item):
        s = item.get("summary", "")
        s2 = re.sub(r"\s+", " ", s).strip()
        if s2 != s:
            item["summary"] = s2
            fixes.append(f"{item['ref']}: 要約の改行・空白を整えた")
        if "labels" in item:
            labels = []
            for label in item["labels"]:
                fixed = sanitize_label(label)
                if fixed and fixed not in labels:
                    labels.append(fixed)
            if labels != item["labels"]:
                fixes.append(f"{item['ref']}: ラベルを Jira で使える形にした {item['labels']} → {labels}")
                item["labels"] = labels

    for e in plan.get("epics", []):
        fix_item(e)
    for _, it in all_issues(plan):
        fix_item(it)
        for st in it.get("subtasks", []):
            fix_item(st)
    return fixes


# ---------------------------------------------------------------- 検査


def _find_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    stack: list[str] = []

    def dfs(n):
        color[n] = GRAY
        stack.append(n)
        for m in graph.get(n, []):
            if color.get(m) == GRAY:
                return stack[stack.index(m) :] + [m]
            if color.get(m) == WHITE:
                found = dfs(m)
                if found:
                    return found
        stack.pop()
        color[n] = BLACK
        return None

    for n in graph:
        if color[n] == WHITE:
            found = dfs(n)
            if found:
                return found
    return None


def lint(plan: dict, deck_md: str, evidence_threshold: float = 0.85) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        import jsonschema

        for err in jsonschema.Draft202012Validator(PLAN_SCHEMA).iter_errors(plan):
            errors.append(f"スキーマ違反 {'/'.join(map(str, err.absolute_path))}: {err.message}")
    except ImportError:
        warnings.append("jsonschema がないのでスキーマの検査を飛ばした（pip install jsonschema）")
    if errors:
        return {"errors": errors, "warnings": warnings, "stats": {}}

    slides = slides_from_deck(deck_md)
    refs = all_refs(plan)
    dup = sorted({r for r in refs if refs.count(r) > 1})
    if dup:
        errors.append(f"ref が重複している: {dup}")
    ref_set = set(refs)

    cited: set[int] = set()

    def check_item(item, kind):
        ref = item["ref"]
        s = item["summary"]
        if not s.strip():
            errors.append(f"{ref}: 要約が空")
        if len(s) > 255:
            errors.append(f"{ref}: 要約が255字を超える（Jira の上限）")
        elif len(s) > 100:
            warnings.append(f"{ref}: 要約が長い（{len(s)}字）")
        if "\n" in s:
            errors.append(f"{ref}: 要約に改行がある")
        bad = [x for x in item.get("labels", []) if x != sanitize_label(x)]
        if bad:
            errors.append(f"{ref}: ラベル {bad} は Jira で使えない（空白・記号）。--fix で直せる")
        for n in item.get("source_slides", []):
            if n not in slides:
                errors.append(f"{ref}: 出典のスライド {n} が資料にない")
        cited.update(item.get("source_slides", []))
        # 要約・受け入れ条件の数字は、出典のスライドにあるはず（300ms → 200ms のような書き換えを拾う）
        scope_all = "\n".join(slides.get(n, "") for n in item.get("source_slides", [])) or deck_md
        stated = " ".join([item["summary"]] + item.get("acceptance_criteria", []))
        bad_nums = invented_numbers(scope_all, stated)
        if bad_nums:
            warnings.append(f"{ref}: 要約・受け入れ条件の数字 {bad_nums} が出典のスライドにない")
        if kind != "epic":
            if not item.get("source_slides"):
                errors.append(f"{ref}: 出典のスライドがない")
            ev = item.get("evidence", [])
            if not ev:
                errors.append(f"{ref}: 根拠の引用（evidence）がない")
            # 根拠は出典のスライドで探す。見つからなければ資料全体で探し、あれば出典の書き間違いとして警告にとどめる
            scope = "\n".join(slides.get(n, "") for n in item.get("source_slides", []))
            for q in ev:
                cov_here, _ = coverage([q], scope, evidence_threshold)
                if cov_here >= 1.0:
                    continue
                cov_all, _ = coverage([q], deck_md, evidence_threshold)
                if cov_all >= 1.0:
                    warnings.append(f"{ref}: 根拠「{q[:40]}」は出典のスライド {item.get('source_slides')} ではなく別のスライドにある")
                else:
                    errors.append(f"{ref}: 根拠「{q[:40]}」が資料にない（作り話の疑い）")

    for e in plan["epics"]:
        check_item(e, "epic")
        if not e["issues"]:
            warnings.append(f"{e['ref']}: 課題のないエピック")
    graph: dict[str, list[str]] = {}
    summaries: list[tuple[str, str]] = []
    for _, it in all_issues(plan):
        check_item(it, "issue")
        for st in it["subtasks"]:
            check_item(st, "subtask")
        summaries.append((it["ref"], normalize(it["summary"])))
        for d in it["depends_on"]:
            if d not in ref_set:
                errors.append(f"{it['ref']}: 依存先 {d} がない")
            elif d == it["ref"]:
                errors.append(f"{it['ref']}: 自分自身に依存している")
        graph[it["ref"]] = [d for d in it["depends_on"] if d in ref_set and d != it["ref"]]
        if it["due_date"]:
            try:
                due = date.fromisoformat(it["due_date"])
            except ValueError:
                errors.append(f"{it['ref']}: 期限 {it['due_date']} が YYYY-MM-DD でない")
            else:
                if "due_date" not in it["inferred_fields"]:
                    # 推測でない期限なら、月か日の数字が根拠か出典スライドにあるはず
                    scope = " ".join(it["evidence"]) + " ".join(slides.get(n, "") for n in it["source_slides"])
                    nums = numbers_in(scope)
                    if str(due.month) not in nums and str(due.day) not in nums and due.isoformat() not in scope:
                        warnings.append(f"{it['ref']}: 期限 {it['due_date']} の数字が資料に見当たらない。推測なら inferred_fields に due_date を入れる")
        if it["assignee_hint"]:
            scope = " ".join(slides.get(n, "") for n in it["source_slides"])
            if normalize(it["assignee_hint"]) not in normalize(scope):
                warnings.append(f"{it['ref']}: 担当「{it['assignee_hint']}」が出典のスライドに見当たらない")
    cycle = _find_cycle(graph)
    if cycle:
        errors.append(f"依存が循環している: {' → '.join(cycle)}")

    for i in range(len(summaries)):
        for j in range(i + 1, len(summaries)):
            if summaries[i][1] and SequenceMatcher(None, summaries[i][1], summaries[j][1]).ratio() > 0.9:
                warnings.append(f"{summaries[i][0]} と {summaries[j][0]}: 要約がほぼ同じ（重複の疑い）")

    for q in plan["open_questions"]:
        cited.update(q["source_slides"])
    skipped = {s["slide"] for s in plan["skipped_slides"]}
    for n in sorted(slides):
        if n not in cited and n not in skipped:
            warnings.append(f"スライド {n}: どの課題にも使われておらず、除外の理由もない（取りこぼしの疑い）")

    n_issues = sum(1 for _ in all_issues(plan))
    n_sub = sum(len(it["subtasks"]) for _, it in all_issues(plan))
    stats = {"epics": len(plan["epics"]), "issues": n_issues, "subtasks": n_sub, "open_questions": len(plan["open_questions"]), "slides": len(slides), "slides_cited": len(cited & set(slides))}
    return {"errors": errors, "warnings": warnings, "stats": stats}


def main(argv=None):
    ap = argparse.ArgumentParser(description="issues.json を資料（deck.md）と突き合わせて検査する")
    ap.add_argument("issues", type=Path, nargs="?")
    ap.add_argument("--deck", type=Path)
    ap.add_argument("--fix", action="store_true", help="意味を変えない直し（ラベル・空白）をして上書きする")
    ap.add_argument("--print-schema", action="store_true")
    args = ap.parse_args(argv)
    if args.print_schema:
        print(json.dumps(PLAN_SCHEMA, ensure_ascii=False, indent=1))
        return 0
    if not (args.issues and args.deck):
        ap.error("issues.json と --deck が要る")
    data = read_json(args.issues)
    plan = data.get("plan", data)
    fixes = autofix(plan) if args.fix else []
    if args.fix and fixes:
        args.issues.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = lint(plan, args.deck.read_text(encoding="utf-8"))
    result["fixes"] = fixes
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
