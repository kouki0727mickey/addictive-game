"""テスト用の偽サーバー: vLLM（OpenAI 互換）と Jira REST。実物なしで配線と検証ロジックを確かめる。

偽 vLLM は原文の JSON をそのまま Markdown にして返す「理想の VLM」を戯画化したもの。
mode で「文字を落とす」「1回目だけ落とす」「数字を作る」を再現する。モデルの性能を示すものではない。
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


def _source_to_md(src: dict) -> list[str]:
    lines = []
    for b in src["blocks"]:
        if b["type"] == "text":
            for p in b["paragraphs"]:
                lines.append(("  " * p["level"]) + (f"{p['bullet']} " if p["bullet"] else "") + p["text"])
        elif b["type"] in ("table", "chart"):
            lines.append("{{" + b["id"] + "}}")
        elif b["type"] == "image":
            lines.append(f"> 図（{b['name']}）: 説明。図中の文字「Gateway」")
        elif b["type"] == "diagram":
            lines += ["- " + i["text"] for i in b["items"]]
    return lines


class _Server:
    def __init__(self, handler_cls):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self.httpd.owner = self
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


class _JSONHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body=None, headers=None):
        raw = b"" if body is None else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("application/json") and raw:
            return json.loads(raw)
        return raw


class MockVLLM(_Server):
    """mode: good / lossy_once / lossy / invent / flaky（1回目は 503）"""

    def __init__(self, mode="good"):
        self.mode = mode
        self.calls = []
        super().__init__(_VLLMHandler)


class _VLLMHandler(_JSONHandler):
    def do_POST(self):
        owner: MockVLLM = self.server.owner
        body = self._body()
        owner.calls.append(body)
        if owner.mode == "flaky" and len(owner.calls) == 1:
            return self._send(503, {"error": "busy"})
        user = [m for m in body["messages"] if m["role"] == "user"]
        first = user[0]["content"][0]["text"]
        src = json.loads(first.split("\n", 1)[1])
        lines = _source_to_md(src)
        is_retry = len(user) > 1
        if owner.mode == "lossy" or (owner.mode == "lossy_once" and not is_retry):
            lines = lines[: max(1, len(lines) // 2)]
        if owner.mode == "invent" or (owner.mode == "invent_once" and not is_retry):
            lines.append("- 売上は 98765 円増える")
        text = "<think>考え中</think>```markdown\n## " + (src.get("title") or "") + "\n" + "\n".join(lines) + "\n```"
        self._send(200, {"choices": [{"message": {"content": text}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}})


class MockJira(_Server):
    """Jira Cloud（v3）/ Data Center（v2）の最小限の REST。課題は self.issues に入る。"""

    def __init__(self, deployment="Cloud", lang="ja", fail_once_429=False, reject_summary=None):
        self.reject_summary = reject_summary
        self.deployment = deployment
        self.lang = lang
        self.issues: dict[str, dict] = {}
        self.links: list[dict] = []
        self.attachments: dict[str, list[str]] = {}
        self.requests: list[tuple[str, str]] = []
        self.fail_once_429 = fail_once_429
        self.seq = 0
        super().__init__(_JiraHandler)

    def issue_types(self):
        if self.lang == "ja":
            names = {"epic": "エピック", "story": "ストーリー", "task": "タスク", "bug": "バグ", "sub": "サブタスク"}
        else:
            names = {"epic": "Epic", "story": "Story", "task": "Task", "bug": "Bug", "sub": "Sub-task"}
        return [
            {"id": "10000", "name": names["epic"], "subtask": False, "hierarchyLevel": 1},
            {"id": "10001", "name": names["story"], "subtask": False, "hierarchyLevel": 0},
            {"id": "10002", "name": names["task"], "subtask": False, "hierarchyLevel": 0},
            {"id": "10003", "name": names["bug"], "subtask": False, "hierarchyLevel": 0},
            {"id": "10004", "name": names["sub"], "subtask": True, "hierarchyLevel": -1},
        ]


class _JiraHandler(_JSONHandler):
    def _api(self):
        owner: MockJira = self.server.owner
        path = urlparse(self.path).path
        m = re.match(r"^/rest/api/(2|3)(/.*)$", path)
        return owner, (m.group(1) if m else None), (m.group(2) if m else path)

    def do_GET(self):
        owner, ver, path = self._api()
        owner.requests.append(("GET", self.path))
        q = parse_qs(urlparse(self.path).query)
        if path == "/serverInfo":
            return self._send(200, {"deploymentType": owner.deployment, "version": "10.0.0" if owner.deployment != "Cloud" else "1001.0.0"})
        if path == "/myself":
            return self._send(200, {"accountId": "abc", "displayName": "Test User"})
        m = re.match(r"^/project/(\w+)$", path)
        if m:
            if m.group(1) != "PAY":
                return self._send(404, {"errorMessages": ["No project could be found with key"]})
            return self._send(200, {"id": "10100", "key": "PAY", "name": "Payments", "issueTypes": owner.issue_types(), "style": "classic"})
        m = re.match(r"^/issue/createmeta/(\w+)/issuetypes/(\d+)$", path)
        if m:
            fields = [
                {"fieldId": "summary", "required": True, "name": "Summary"},
                {"fieldId": "issuetype", "required": True, "name": "Issue Type"},
                {"fieldId": "project", "required": True, "name": "Project"},
                {"fieldId": "description", "required": False, "name": "Description"},
                {"fieldId": "labels", "required": False, "name": "Labels"},
                {"fieldId": "priority", "required": False, "name": "Priority", "allowedValues": [{"id": "1", "name": "Highest"}, {"id": "2", "name": "High"}, {"id": "3", "name": "Medium"}, {"id": "4", "name": "Low"}]},
                {"fieldId": "duedate", "required": False, "name": "Due date"},
                {"fieldId": "parent", "required": False, "name": "Parent"},
            ]
            if owner.deployment != "Cloud" and m.group(2) == "10000":
                fields.append({"fieldId": "customfield_10011", "required": True, "name": "Epic Name"})
            if owner.deployment != "Cloud" and m.group(2) in ("10001", "10002", "10003"):
                fields.append({"fieldId": "customfield_10014", "required": False, "name": "Epic Link"})
            return self._send(200, {"values": fields, "fields": fields})
        m = re.match(r"^/issue/([\w-]+)$", path)
        if m:
            key = m.group(1)
            if key not in owner.issues:
                return self._send(404, {"errorMessages": ["Issue does not exist"]})
            links = []
            for ln in owner.links:
                if ln["inwardIssue"]["key"] == key:  # key is blocked by outward
                    links.append({"type": {"name": ln["type"]["name"]}, "inwardIssue": {"key": ln["outwardIssue"]["key"]}})
                if ln["outwardIssue"]["key"] == key:
                    links.append({"type": {"name": ln["type"]["name"]}, "outwardIssue": {"key": ln["inwardIssue"]["key"]}})
            return self._send(200, {"key": key, "fields": {"issuelinks": links}})
        if path == "/issueLinkType":
            return self._send(200, {"issueLinkTypes": [{"id": "1", "name": "Blocks", "inward": "is blocked by", "outward": "blocks"}, {"id": "2", "name": "Relates"}]})
        if path in ("/search", "/search/jql"):
            jql = q.get("jql", [""])[0]
            m = re.search(r'labels\s*=\s*"([^"]+)"', jql)
            label = m.group(1) if m else None
            found = [
                {"key": k, "fields": {"summary": v["fields"]["summary"], "labels": v["fields"].get("labels", []), "issuetype": {"name": v["type_name"]}}}
                for k, v in owner.issues.items()
                if label is None or label in v["fields"].get("labels", [])
            ]
            return self._send(200, {"issues": found, "total": len(found), "isLast": True})
        return self._send(404, {"errorMessages": [f"not found {path}"]})

    def do_POST(self):
        owner, ver, path = self._api()
        owner.requests.append(("POST", self.path))
        if owner.fail_once_429:
            owner.fail_once_429 = False
            return self._send(429, {"errorMessages": ["rate limited"]}, {"Retry-After": "0"})
        if path == "/issue":
            body = self._body()
            f = body["fields"]
            errors = {}
            if owner.reject_summary and owner.reject_summary in f.get("summary", ""):
                errors["summary"] = "rejected by mock"
            if not f.get("summary"):
                errors["summary"] = "required"
            if len(f.get("summary", "")) > 255:
                errors["summary"] = "too long"
            if any(" " in label for label in f.get("labels", [])):
                errors["labels"] = "no spaces"
            types = {t["id"]: t for t in owner.issue_types()}
            it = types.get(f.get("issuetype", {}).get("id"))
            if not it:
                errors["issuetype"] = "invalid"
            elif it["subtask"] and "parent" not in f:
                errors["parent"] = "subtask needs parent"
            if ver == "3" and isinstance(f.get("description"), str):
                errors["description"] = "Operation value must be an Atlassian Document"
            if ver == "2" and isinstance(f.get("description"), dict):
                errors["description"] = "must be a string"
            if owner.deployment != "Cloud" and it and it["id"] == "10000" and not f.get("customfield_10011"):
                errors["customfield_10011"] = "Epic Name is required."
            if errors:
                return self._send(400, {"errorMessages": [], "errors": errors})
            owner.seq += 1
            key = f"PAY-{owner.seq}"
            owner.issues[key] = {"fields": f, "type_name": it["name"]}
            return self._send(201, {"id": str(10000 + owner.seq), "key": key, "self": f"{owner.url}/rest/api/{ver}/issue/{key}"})
        if path == "/issueLink":
            owner.links.append(self._body())
            return self._send(201)
        m = re.match(r"^/issue/([\w-]+)/attachments$", path)
        if m:
            if self.headers.get("X-Atlassian-Token") != "no-check":
                return self._send(403, {"errorMessages": ["XSRF check failed"]})
            self._body()
            owner.attachments.setdefault(m.group(1), []).append("file")
            return self._send(200, [{"id": "1"}])
        return self._send(404, {"errorMessages": [f"not found {path}"]})
