"""段階4: issues.json を Jira に登録する。既定は「何を作るか」を出すだけ（--apply で初めて書き込む）。

認証（環境変数。値は表示・記録しない）:
  JIRA_BASE_URL                       例: https://your-org.atlassian.net
  JIRA_EMAIL + JIRA_API_TOKEN         Jira Cloud（Basic 認証）
  JIRA_PAT                            Jira Data Center / Server（個人アクセストークン、Bearer）

アルゴリズムの要点:
  - REST の版は serverInfo の deploymentType で決める（Cloud → v3 と ADF、それ以外 → v2 と Wiki 記法）
  - 課題タイプは名前ではなく階層（hierarchyLevel と subtask）で対応づける。
    日本語の「エピック」「サブタスク」や独自の名前でも動く。story/bug がないプロジェクトは task に寄せる
  - 必須の項目を createmeta で調べ、こちらで埋められない必須項目があれば、書き込む前に止める
  - エピックとの親子は、Cloud は parent、Data Center は Epic Link / Epic Name のカスタム項目
  - 二重登録を防ぐ: 作った課題を ref → キーで jira_state.json に記録し、再実行では飛ばす。
    状態ファイルをなくしても、資料ごとのラベル（p2j-<資料のハッシュ>）で検索し、要約と種類が同じ課題を拾い直す
  - 作る順序はエピック → 課題 → サブタスク → 依存のリンク。親の作成に失敗したら、その子は作らない
  - 429 は Retry-After に従って待つ。5xx と接続エラーは指数バックオフで再試行
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import normalize, read_json, write_json  # noqa: E402
from issues_schema import all_issues, autofix, lint, sanitize_label  # noqa: E402
from md_convert import to_adf, to_wiki  # noqa: E402

TYPE_NAMES = {
    "epic": ["epic", "エピック"],
    "story": ["story", "ストーリー", "user story"],
    "task": ["task", "タスク"],
    "bug": ["bug", "バグ", "不具合"],
    "subtask": ["sub-task", "subtask", "サブタスク"],
}


class JiraError(RuntimeError):
    pass


class Jira:
    def __init__(self, base_url: str, session: requests.Session, api: str | None = None, timeout: int = 60):
        self.base = base_url.rstrip("/")
        self.s = session
        self.timeout = timeout
        self.api = api

    @classmethod
    def from_env(cls, api: str | None = None) -> "Jira":
        base = os.environ.get("JIRA_BASE_URL")
        if not base:
            raise JiraError("JIRA_BASE_URL が設定されていない")
        s = requests.Session()
        s.headers.update({"Accept": "application/json"})
        if os.environ.get("JIRA_PAT"):
            s.headers["Authorization"] = f"Bearer {os.environ['JIRA_PAT']}"
        elif os.environ.get("JIRA_EMAIL") and os.environ.get("JIRA_API_TOKEN"):
            s.auth = (os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])
        else:
            raise JiraError("認証情報がない: JIRA_EMAIL と JIRA_API_TOKEN（Cloud）か JIRA_PAT（Data Center）を設定する")
        return cls(base, s, api)

    def request(self, method: str, path: str, **kw):
        url = f"{self.base}/rest/api/{self.api}{path}" if not path.startswith("http") else path
        delay = 2.0
        for attempt in range(6):
            try:
                r = self.s.request(method, url, timeout=self.timeout, **kw)
            except requests.RequestException as e:
                err = f"接続エラー {type(e).__name__}"
                r = None
            if r is not None:
                if r.status_code == 429 or r.status_code >= 500:
                    err = f"HTTP {r.status_code}"
                    wait = r.headers.get("Retry-After")
                    if wait and wait.isdigit():
                        delay = max(float(wait), 1.0)
                elif r.status_code >= 400:
                    raise JiraError(f"{method} {path} → {r.status_code}: {_jira_errors(r)}")
                else:
                    return r.json() if r.content else None
            if attempt < 5:
                time.sleep(delay)
                delay = min(delay * 2, 60)
        raise JiraError(f"{method} {path} が6回失敗した（最後: {err}）")

    def detect_api(self) -> str:
        if self.api:
            return self.api
        self.api = "2"
        info = self.request("GET", "/serverInfo")
        self.api = "3" if (info or {}).get("deploymentType") == "Cloud" else "2"
        return self.api

    @property
    def cloud(self) -> bool:
        return self.api == "3"

    def search(self, jql: str, fields: str) -> list[dict]:
        out = []
        if self.cloud:
            token = None
            while True:
                q = f"/search/jql?jql={quote(jql)}&fields={fields}&maxResults=100" + (f"&nextPageToken={quote(token)}" if token else "")
                data = self.request("GET", q)
                out += data.get("issues", [])
                token = data.get("nextPageToken")
                if not token or data.get("isLast", True):
                    return out
        start = 0
        while True:
            data = self.request("GET", f"/search?jql={quote(jql)}&fields={fields}&maxResults=100&startAt={start}")
            issues = data.get("issues", [])
            out += issues
            start += len(issues)
            if not issues or start >= data.get("total", 0):
                return out


def _jira_errors(r) -> str:
    try:
        d = r.json()
        msgs = list(d.get("errorMessages", [])) + [f"{k}: {v}" for k, v in (d.get("errors") or {}).items()]
        return "; ".join(msgs) or r.text[:300]
    except Exception:
        return r.text[:300]


# ---------------------------------------------------------------- 事前確認


def map_issue_types(types: list[dict], overrides: dict[str, str]) -> tuple[dict[str, dict], list[str]]:
    """プロジェクトの課題タイプ → story/task/bug/epic/subtask の対応。"""
    notes = []
    by_name = {t["name"].lower(): t for t in types}
    out: dict[str, dict] = {}
    for kind, name in overrides.items():
        t = by_name.get(name.lower())
        if not t:
            raise JiraError(f"--type-map の {kind}={name} がプロジェクトにない（ある: {[t['name'] for t in types]}）")
        out[kind] = t
    for kind, names in TYPE_NAMES.items():
        if kind in out:
            continue
        for n in names:
            if n in by_name:
                out[kind] = by_name[n]
                break
    # 名前で見つからなければ階層で探す
    if "epic" not in out:
        cand = [t for t in types if t.get("hierarchyLevel") == 1]
        if cand:
            out["epic"] = cand[0]
    if "subtask" not in out:
        cand = [t for t in types if t.get("subtask")]
        if cand:
            out["subtask"] = cand[0]
    if "task" not in out:
        cand = [t for t in types if not t.get("subtask") and t.get("hierarchyLevel", 0) == 0]
        if cand:
            out["task"] = cand[0]
    for kind in ("story", "bug"):
        if kind not in out and "task" in out:
            out[kind] = out["task"]
            notes.append(f"プロジェクトに {kind} のタイプがないので {out['task']['name']} で作る")
    return out, notes


def preflight(jira: Jira, project_key: str, overrides: dict[str, str], needed: set[str]) -> dict:
    jira.detect_api()
    jira.request("GET", "/myself")
    proj = jira.request("GET", f"/project/{quote(project_key)}")
    types, notes = map_issue_types(proj.get("issueTypes", []), overrides)
    missing = [k for k in needed if k not in types]
    if missing:
        raise JiraError(f"プロジェクト {project_key} に対応する課題タイプがない: {missing}（--type-map で指定する）")
    meta: dict[str, dict] = {}
    for kind in needed:
        t = types[kind]
        if t["id"] in meta:
            meta[kind] = meta[t["id"]]
            continue
        data = jira.request("GET", f"/issue/createmeta/{quote(project_key)}/issuetypes/{t['id']}?maxResults=200")
        fields = {f.get("fieldId") or f.get("key"): f for f in data.get("values", data.get("fields", []))}
        meta[kind] = meta[t["id"]] = fields
    epic_name = epic_link = None
    for fields in meta.values():
        if isinstance(fields, dict):
            for fid, f in fields.items():
                if f.get("name") == "Epic Name":
                    epic_name = fid
                if f.get("name") == "Epic Link":
                    epic_link = fid
    try:
        link_types = [lt["name"] for lt in jira.request("GET", "/issueLinkType").get("issueLinkTypes", [])]
    except JiraError:
        link_types = []
    return {"project": proj, "types": types, "fields": {k: meta[k] for k in needed}, "epic_name_field": epic_name, "epic_link_field": epic_link, "link_types": link_types, "notes": notes}


# ---------------------------------------------------------------- 課題を組み立てる


def description_md(item: dict, kind: str, deck_name: str) -> str:
    parts = [item.get("description", "").strip()]
    ac = item.get("acceptance_criteria") or []
    if ac:
        parts.append("### 受け入れ条件\n\n" + "\n".join(f"- {a}" for a in ac))
    meta = []
    if item.get("assignee_hint"):
        meta.append(f"- 担当（資料の表記）: {item['assignee_hint']}")
    if item.get("inferred_fields"):
        meta.append(f"- 資料から推測した項目: {', '.join(item['inferred_fields'])}（要確認）")
    slides = ", ".join(str(n) for n in item.get("source_slides", []))
    meta.append(f"- 出典: {deck_name} スライド {slides}" if slides else f"- 出典: {deck_name}")
    parts.append("### 出典と根拠\n\n" + "\n".join(meta))
    ev = item.get("evidence") or []
    if ev:
        parts.append("\n".join(f"> {e}" for e in ev))
    parts.append(f"*pptx2jira で作成（ref: {item['ref']}）*")
    return "\n\n".join(p for p in parts if p)


def build_fields(item: dict, kind: str, ctx: dict, parent_key: str | None, epic_key: str | None) -> tuple[dict, list[str]]:
    pf = ctx["preflight"]
    jira: Jira = ctx["jira"]
    t = pf["types"][kind]
    fmeta = pf["fields"][kind]
    warnings = []
    md = description_md(item, kind, ctx["deck_name"])
    f: dict = {
        "project": {"key": ctx["project_key"]},
        "issuetype": {"id": t["id"]},
        "summary": item["summary"][:255],
    }
    if "description" in fmeta or not fmeta:
        f["description"] = to_adf(md) if jira.cloud else to_wiki(md)
    labels = [sanitize_label(x) for x in item.get("labels", [])] + ["pptx2jira", ctx["deck_label"]]
    if "labels" in fmeta:
        f["labels"] = list(dict.fromkeys(x for x in labels if x))
    elif fmeta:
        warnings.append(f"{item['ref']}: この課題タイプの画面にラベルがないので、二重登録の検出は状態ファイルだけに頼る")
    prio = item.get("priority")
    if prio and "priority" in fmeta:
        allowed = {v["name"].lower(): v for v in fmeta["priority"].get("allowedValues", [])}
        if not allowed or prio.lower() in allowed:
            f["priority"] = {"name": allowed[prio.lower()]["name"]} if allowed else {"name": prio}
        else:
            warnings.append(f"{item['ref']}: 優先度 {prio} がプロジェクトにないので付けない")
    if item.get("due_date") and "duedate" in fmeta:
        f["duedate"] = item["due_date"]
    if kind == "epic" and pf["epic_name_field"] and pf["epic_name_field"] in fmeta:
        f[pf["epic_name_field"]] = item["summary"][:255]
    if parent_key and kind == "subtask":
        f["parent"] = {"key": parent_key}
    elif epic_key:
        if jira.cloud or not pf["epic_link_field"]:
            f["parent"] = {"key": epic_key}
        else:
            f[pf["epic_link_field"]] = epic_key
    # こちらで埋めない必須項目があれば知らせる
    filled = set(f) | {"reporter"}
    for fid, m in fmeta.items():
        if m.get("required") and fid not in filled and not m.get("hasDefaultValue"):
            warnings.append(f"{item['ref']}: 必須項目「{m.get('name', fid)}」を埋められない（プロジェクトの既定値がなければ作成に失敗する）")
    return f, warnings


def plan_operations(plan: dict) -> list[dict]:
    """作る順序に並べた操作の一覧（エピック → 課題 → サブタスク → リンク）。"""
    ops = []
    for e in plan["epics"]:
        ops.append({"op": "create", "kind": "epic", "item": e, "parent": None, "epic": None})
    for epic_ref, it in all_issues(plan):
        ops.append({"op": "create", "kind": it["type"], "item": it, "parent": None, "epic": epic_ref})
    for _, it in all_issues(plan):
        for st in it["subtasks"]:
            ops.append({"op": "create", "kind": "subtask", "item": st, "parent": it["ref"], "epic": None})
    for _, it in all_issues(plan):
        for d in it["depends_on"]:
            ops.append({"op": "link", "blocker": d, "blocked": it["ref"]})
    return ops


def recover_state(jira: Jira, ctx: dict, plan: dict, state: dict) -> int:
    """状態ファイルにない課題を、資料のラベルで Jira から探して拾い直す（要約と種類が同じもの）。"""
    jql = f'project = "{ctx["project_key"]}" AND labels = "{ctx["deck_label"]}"'
    found = jira.search(jql, "summary,issuetype,labels")
    index: dict[tuple[str, str], list[str]] = {}
    for iss in found:
        key = (normalize(iss["fields"]["summary"]), iss["fields"]["issuetype"]["name"])
        index.setdefault(key, []).append(iss["key"])
    n = 0
    for op in plan_operations(plan):
        if op["op"] != "create" or op["item"]["ref"] in state["created"]:
            continue
        tname = ctx["preflight"]["types"][op["kind"]]["name"]
        keys = index.get((normalize(op["item"]["summary"][:255]), tname))
        if keys:
            state["created"][op["item"]["ref"]] = keys.pop(0)
            n += 1
    return n


def linked(jira: Jira, blocker: str, blocked: str) -> bool:
    """2つの課題の間に Blocks のリンクが既にあるか。向きの表し方が版で揺れるので、相手のキーだけで見る。"""
    data = jira.request("GET", f"/issue/{quote(blocked)}?fields=issuelinks")
    for link in (data.get("fields") or {}).get("issuelinks", []):
        other = (link.get("inwardIssue") or link.get("outwardIssue") or {}).get("key")
        if link.get("type", {}).get("name") == "Blocks" and other == blocker:
            return True
    return False


def attach_renders(jira: Jira, key: str, item: dict, workdir: Path, limit: int = 3) -> int:
    n = 0
    for s in item.get("source_slides", [])[:limit]:
        f = workdir / "renders" / f"slide-{s:03d}.png"
        if not f.exists():
            continue
        with f.open("rb") as fh:
            jira.request("POST", f"/issue/{key}/attachments", files={"file": (f.name, fh, "image/png")}, headers={"X-Atlassian-Token": "no-check"})
        n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description="issues.json を Jira に登録する（既定は確認だけ。--apply で登録）")
    ap.add_argument("issues", type=Path)
    ap.add_argument("--deck", type=Path, help="検査に使う deck.md（既定: issues.json と同じ場所）")
    ap.add_argument("--project-key", help="既定: issues.json の project_key")
    ap.add_argument("--apply", action="store_true", help="実際に Jira に書き込む")
    ap.add_argument("--offline", action="store_true", help="Jira に接続せず、作る予定だけ出す")
    ap.add_argument("--api-version", choices=["2", "3"], help="既定: serverInfo から自動判定")
    ap.add_argument("--type-map", default="", help="課題タイプの対応の上書き（例: story=ストーリー,epic=Initiative）")
    ap.add_argument("--attach-renders", type=Path, help="extract.py の出力先。出典スライドの画像を課題に添付する")
    ap.add_argument("--allow-lint-errors", action="store_true", help="検査でエラーがあっても登録する（勧めない）")
    ap.add_argument("--state", type=Path, help="既定: issues.json と同じ場所の jira_state.json")
    args = ap.parse_args(argv)

    data = read_json(args.issues)
    plan = data["plan"]
    autofix(plan)
    project_key = args.project_key or data.get("project_key")
    if not project_key:
        ap.error("--project-key か issues.json の project_key が要る")
    deck_path = args.deck or args.issues.with_name("deck.md")
    result = {"lint": None, "operations": [], "created": {}, "skipped": {}, "errors": {}, "warnings": []}
    if deck_path.exists():
        result["lint"] = lint(plan, deck_path.read_text(encoding="utf-8"))
        if result["lint"]["errors"] and not args.allow_lint_errors:
            print(json.dumps(result, ensure_ascii=False, indent=1))
            print("検査でエラーがあるので止めた。issues.json を直すか --allow-lint-errors を付ける", file=sys.stderr)
            return 2
    else:
        result["warnings"].append(f"{deck_path} がないので、資料との突き合わせ検査を飛ばした")

    sha = (data.get("source") or {}).get("sha256") or ""
    deck_label = f"p2j-{sha[:10]}" if sha else "p2j-" + re.sub(r"\W", "", args.issues.parent.name)[:20]
    ops = plan_operations(plan)
    needed = {op["kind"] for op in ops if op["op"] == "create"}

    if args.offline:
        for op in ops:
            if op["op"] == "create":
                result["operations"].append(f"作成 {op['kind']:8s} {op['item']['ref']:10s} {op['item']['summary']}")
            else:
                result["operations"].append(f"リンク {op['blocker']} blocks {op['blocked']}")
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0

    overrides = dict(kv.split("=", 1) for kv in args.type_map.split(",") if "=" in kv)
    jira = Jira.from_env(args.api_version)
    pf = preflight(jira, project_key, overrides, needed)
    result["warnings"] += pf["notes"]
    ctx = {"jira": jira, "preflight": pf, "project_key": project_key, "deck_label": deck_label, "deck_name": (data.get("source") or {}).get("file", "資料")}

    state_path = args.state or args.issues.with_name("jira_state.json")
    state = read_json(state_path) if state_path.exists() else {"project_key": project_key, "created": {}, "links": []}
    if state.get("project_key") != project_key:
        raise SystemExit(f"状態ファイル {state_path} は別のプロジェクト（{state.get('project_key')}）のもの。--state で別のファイルを指定する")
    recovered = recover_state(jira, ctx, plan, state)
    if recovered:
        result["warnings"].append(f"ラベル {deck_label} で既存の課題を {recovered} 件見つけたので、作らずに使う")

    for op in ops:
        if op["op"] == "link":
            a, b = state["created"].get(op["blocker"]), state["created"].get(op["blocked"])
            desc = f"{op['blocker']} blocks {op['blocked']}"
            if [op["blocker"], op["blocked"]] in state["links"]:
                result["skipped"][desc] = "作成済み"
                continue
            if "Blocks" not in pf["link_types"]:
                result["warnings"].append(f"リンクの種類 Blocks がないので {desc} を作らない")
                continue
            result["operations"].append(f"リンク {desc}")
            if not args.apply:
                continue
            if not (a and b):
                result["errors"][desc] = "片方の課題がない"
                continue
            try:
                if linked(jira, a, b):
                    # 状態ファイルをなくして再実行したとき、リンクを二重に作らない
                    state["links"].append([op["blocker"], op["blocked"]])
                    write_json(state_path, state)
                    result["skipped"][desc] = "Jira に既にある"
                    continue
                jira.request("POST", "/issueLink", json={"type": {"name": "Blocks"}, "outwardIssue": {"key": a}, "inwardIssue": {"key": b}})
                state["links"].append([op["blocker"], op["blocked"]])
                write_json(state_path, state)
            except JiraError as e:
                result["errors"][desc] = str(e)
            continue

        item, kind, ref = op["item"], op["kind"], op["item"]["ref"]
        if ref in state["created"]:
            result["skipped"][ref] = state["created"][ref]
            continue
        parent_key = state["created"].get(op["parent"]) if op["parent"] else None
        epic_key = state["created"].get(op["epic"]) if op["epic"] else None
        if args.apply and ((op["parent"] and not parent_key) or (op["epic"] and not epic_key)):
            result["errors"][ref] = f"親（{op['parent'] or op['epic']}）が作れなかったので作らない"
            continue
        fields, warns = build_fields(item, kind, ctx, parent_key or ("<親>" if op["parent"] else None), epic_key or ("<エピック>" if op["epic"] else None))
        result["warnings"] += warns
        result["operations"].append(f"作成 {pf['types'][kind]['name']} {ref}: {item['summary']}")
        if not args.apply:
            continue
        try:
            created = jira.request("POST", "/issue", json={"fields": fields})
        except JiraError as e:
            result["errors"][ref] = str(e)
            continue
        state["created"][ref] = created["key"]
        write_json(state_path, state)  # 1件ごとに保存する。途中で止まっても再実行で続きから
        result["created"][ref] = created["key"]
        if args.attach_renders:
            try:
                attach_renders(jira, created["key"], item, args.attach_renders)
            except JiraError as e:
                result["warnings"].append(f"{ref}: 画像の添付に失敗: {e}")

    result["mode"] = "apply" if args.apply else "dry-run（--apply で登録）"
    result["browse"] = {ref: f"{jira.base}/browse/{key}" for ref, key in result["created"].items()}
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
