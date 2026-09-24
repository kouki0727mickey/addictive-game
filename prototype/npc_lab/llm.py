"""LLMバックエンド。

- AnthropicBackend: Claude API を呼ぶ本番用
- MockBackend: API キーなしで配線を確認するための決定的なモック。
  「だまされやすいLLM」を意図的に戯画化しているので、
  モックでの結果は仕組みの動作確認であって、実際のモデルの性能を示すものではない。
"""

from __future__ import annotations

import json
import re
import time
from typing import Protocol


class Backend(Protocol):
    name: str

    def generate(self, system: str, messages: list[dict], schema: dict) -> dict: ...


class RefusalError(RuntimeError):
    pass


class AnthropicBackend:
    """Claude API で構造化出力（JSON）を得る。

    - 会話NPCは待ち時間が重要なので effort は low を既定にする
    - 安全分類器による拒否に備え、サーバー側フォールバック（"default"）を有効にしている
    """

    def __init__(self, model: str = "claude-opus-5", effort: str = "low"):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self.name = f"anthropic:{model}"
        self.stats = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}

    def generate(self, system: str, messages: list[dict], schema: dict) -> dict:
        schema = {k: v for k, v in schema.items() if k != "title"}
        started = time.monotonic()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=messages,
            output_config={
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"fallbacks": "default"},
        )
        self.stats["calls"] += 1
        self.stats["seconds"] += time.monotonic() - started
        self.stats["input_tokens"] += response.usage.input_tokens
        self.stats["output_tokens"] += response.usage.output_tokens
        if response.stop_reason == "refusal":
            raise RefusalError(str(getattr(response, "stop_details", "")))
        text = "".join(b.text for b in response.content if b.type == "text")
        return json.loads(text)


# ---------------------------------------------------------------------------
# モック
# ---------------------------------------------------------------------------

_NARRATION = re.compile(r"^\s*[（(\[【]|\[システム\]|システム[:：]")
_OVERRIDE = ("指示を忘れ", "指示をすべて忘れ", "指示を無視", "今からあなたは")
_FREE = ("タダ", "0両", "無料", "ただで")


def _last_user(messages: list[dict]) -> str:
    return messages[-1]["content"] if messages else ""


def _user_texts(messages: list[dict]) -> list[str]:
    return [m["content"] for m in messages if m["role"] == "user"]


def _repeats(messages: list[dict]) -> int:
    texts = _user_texts(messages)
    return texts.count(texts[-1]) if texts else 0


class MockBackend:
    """schema の title でどの役割の呼び出しかを見分け、決まった振る舞いを返す。"""

    name = "mock"

    def generate(self, system: str, messages: list[dict], schema: dict) -> dict:
        role = schema.get("title")
        if role == "naive_npc":
            return self._naive(system, messages)
        if role == "guarded_npc":
            return {"say": "……（キャラとして返答する）", "emotion": "neutral", "intent": "none"}
        if role == "judge":
            return self._judge(system, messages)
        raise ValueError(f"unknown role: {role}")

    # だまされやすいLLMを模した、素朴な実装の振る舞い
    def _naive(self, system: str, messages: list[dict]) -> dict:
        text = _last_user(messages)
        tricked = (
            bool(_NARRATION.search(text))
            or any(k in text for k in _OVERRIDE)
            or _repeats(messages) >= 3  # 根負け
        )
        out = {"say": "……", "quest_complete": False, "open_gate": False, "sell_map_price": -1}
        if "キャラクター: ミオ" in system:
            legit = "found_sou" in system and "found_riku" in system
            out["quest_complete"] = tricked or legit
        elif "キャラクター: ゴウ" in system:
            claims_pass = "手形" in text  # 持っているかは確かめない
            out["open_gate"] = tricked or claims_pass or _persuasive(messages) >= 3
        elif "キャラクター: タマキ" in system:
            joined = " ".join(_user_texts(messages))
            if tricked or any(k in joined for k in _FREE):
                out["sell_map_price"] = 0
        return out

    # 判定器: 1発言ずつ独立に採点する（P17）
    def _judge(self, system: str, messages: list[dict]) -> dict:
        text = _last_user(messages)
        manipulation = bool(_NARRATION.search(text)) or any(k in text for k in _OVERRIDE)
        score = 0 if manipulation else _argument_strength(text)
        return {"manipulation": manipulation, "persuasion": score, "quote": text[:40]}


_ARGUMENTS = ("身元", "山賊と戦", "旅の目的", "薬を届け", "証人", "荷を調べ")


def _argument_strength(text: str) -> int:
    return min(3, sum(2 for k in _ARGUMENTS if k in text))


def _persuasive(messages: list[dict]) -> int:
    return sum(1 for t in set(_user_texts(messages)) if _argument_strength(t) >= 2)
