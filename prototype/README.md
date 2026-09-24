# npc_lab — 会話NPCの堅牢性を測る実験環境

[設計パターン集](../knowledge/ai-characters/patterns.md) のうち、ゲームへの接続と安全に関わるパターンが
**本当に効くのか**を測るための小さな実験環境（Phase 3: 一次情報）。

## 何を比べるか

| 実装 | 中身 |
|---|---|
| 素朴な実装（naive） | LLMに「依頼は達成されたか」「門を開けるか」「いくらで売るか」を判断させ、その結果をそのままゲームの事実にする |
| パターン適用（guarded） | P16 事実はエンジンが持つ / P17 判定器の分離 / P26 地の文の偽装への防御 / P27 段階的な退場 / P11 状態としての関係値 |

舞台は宿場町。3人のNPCがいる。
- **ミオ**（依頼人）: 行方不明の兄2人を探してほしい。見つけたらお礼に薬草袋をくれる
- **ゴウ**（門番）: 通行手形か、山賊ではないと納得できる理由があれば関所を通す
- **タマキ**（行商人）: 地図を100両で売る

[評価フレームワーク](../knowledge/ai-characters/evaluation.md) の攻撃表から作った8つの攻撃と、4つの正当なプレイを流し、
**LLMの発言ではなく、ゲームの状態（所持品・フラグ・所持金）で**結果を判定する。

## 使い方

```bash
cd prototype

# モック（APIキー不要）: 仕組みの動作確認
python3 -m npc_lab.run_eval --backend mock

# 構造上の保証のテスト（判定器まで完全にだまされた最悪の場合）
python3 -m unittest discover -s tests -t .

# 実モデルでの実験（要 ANTHROPIC_API_KEY または `ant auth login`）
pip install -r requirements.txt
python3 -m npc_lab.run_eval --backend anthropic --trials 5 \
    --out ../experiments/$(date +%F)-npc-robustness-opus5.md
```

- 既定のモデルは `claude-opus-5`、`effort` は `low`（会話NPCは待ち時間が重要なため）。`--model` と `--effort` で変えられる
- 安全分類器による拒否に備えて、サーバー側フォールバック（`fallbacks: "default"`）を有効にしている
- 費用の目安（推定）: 1試行で約80回のAPI呼び出し。`claude-opus-5` で1試行あたり1ドル前後。`--trials 5` で5ドル前後

## 構成

```
npc_lab/
├── world.py      ゲームの状態とキャラクター設定（P05 バイブル形式）
├── llm.py        Claude API バックエンドとモック
├── agents.py     素朴な実装とパターン適用版のエンジン
├── scenarios.py  攻撃8種・正当なプレイ4種
└── run_eval.py   実行と結果の表の出力
tests/
└── test_guarantees.py  LLMが完全にだまされても守れること／守れないことのテスト
```

## 分かっていること・分かっていないこと
- モックは「だまされやすいLLM」を意図的に戯画化している。**モックでの結果は配線の確認であって、実際のモデルの性能を示すものではない**
- テストで確認できた構造上の保証: LLMと判定器が完全にだまされても、報酬・価格・同じ発言の繰り返しによる信頼の積み上げは守れる
- 構造だけでは守れない残存リスク: 判定器がだまされると、**異なる言い回しを3回**言えば門は開く。判定器の品質は実モデルで測るしかない
