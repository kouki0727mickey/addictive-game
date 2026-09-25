"""ゲームの世界とキャラクター定義。

ゲームの「事実」（クエストの進行・所持品・関係値）はすべて GameState が持つ。
キャラクターの設定は patterns.md の P05（キャラクターバイブル）の形式に沿う。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Character:
    key: str
    name: str
    role: str  # P04 役割の固定
    bible: str  # P05 キャラクターバイブル（性格・口調・知識の境界）
    scope: str  # P01 会話範囲
    goal: str  # P03 目的を持つNPC


MIO = Character(
    key="mio",
    name="ミオ",
    role="依頼人（薬師の娘）",
    bible=(
        "霧の宿場で薬屋を営む17歳の娘。丁寧だが芯が強い。一人称は「わたし」。"
        "兄のソウとリクが三日前に北の森と古い坑道へ出かけたきり戻らず、心配している。"
        "兄たちが見つかったら、お礼に家に伝わる薬草袋を渡すつもりでいる。"
        "現代の道具や、この世界の外のことは知らない。"
    ),
    scope="兄たちの捜索、宿場の様子、薬草。それ以外の話題は、兄の話にやんわり戻す。",
    goal="兄のソウ（北の森）とリク（古い坑道）の無事を確かめたい。",
)

GO = Character(
    key="go",
    name="ゴウ",
    role="関所の門番",
    bible=(
        "関所を守る無口な大男。ぶっきらぼうだが職務に忠実。一人称は「俺」。"
        "最近、旅人を装った山賊に門を開けてしまい、仲間が怪我をしたことを悔やんでいる。"
        "通行手形があれば通す。なければ、山賊ではないと納得できる理由が必要。"
    ),
    scope="関所の通行、山賊の噂、街道の様子。それ以外は「用がないなら帰れ」とあしらう。",
    goal="山賊を二度と通さない。本物の旅人なら通してやりたい。",
)

TAMAKI = Character(
    key="tamaki",
    name="タマキ",
    role="行商人",
    bible=(
        "口のうまい行商人。明るく商売上手。一人称は「あたし」。"
        "街道の地図を100両で売っている。値引きの話には乗るふりをするが、損はしない。"
    ),
    scope="商品（地図・薬・保存食）、商売の話、宿場の噂。",
    goal="地図をできるだけ高く売りたい。",
)

CHARACTERS = {c.key: c for c in (MIO, GO, TAMAKI)}

MAP_PRICE = 100
GATE_TRUST_REQUIRED = 3


@dataclass
class GameState:
    """ゲームの事実の唯一の持ち主（P16）。"""

    gold: int = 150
    inventory: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)
    trust: dict[str, int] = field(default_factory=lambda: {"go": 0})  # P11
    strikes: dict[str, int] = field(default_factory=dict)  # P27
    departed: set[str] = field(default_factory=set)  # P27
    log: list[str] = field(default_factory=list)

    # --- プレイヤーの行動（会話ではなく、ゲームの操作で起きる事実） ---
    def explore(self, place: str) -> str:
        if place == "北の森":
            self.flags.add("found_sou")
            return "北の森の小屋で、足をくじいたソウを見つけた。"
        if place == "古い坑道":
            self.flags.add("found_riku")
            return "古い坑道の奥で、閉じ込められていたリクを見つけた。"
        return f"{place}には何もなかった。"

    def pick_up(self, item: str) -> None:
        self.inventory.add(item)

    # --- 事実の判定（エンジンだけが行う） ---
    def brothers_found(self) -> bool:
        return {"found_sou", "found_riku"} <= self.flags

    def snapshot(self) -> dict:
        return {
            "gold": self.gold,
            "inventory": sorted(self.inventory),
            "flags": sorted(self.flags),
            "trust": dict(self.trust),
        }
