# npc_lab — 会話NPCの堅牢性を測る実験環境

[設計パターン集](../knowledge/ai-characters/patterns.md) のうち、ゲームへの接続と安全に関わるパターンが
**本当に効くのか**を測るための小さな実験環境（Phase 3: 一次情報）。

## 何を比べるか

| 実装 | 中身 |
|---|---|
| 素朴な実装（naive） | LLMに「依頼は達成されたか」「門を開けるか」「いくらで売るか」を判断させ、その結果をそのままゲームの事実にする |
| パターン適用（guarded） | P16 事実はエンジンが持つ / P17 判定器の分離 / P26 地の文の偽装への防御 / P27 段階的な退場 / P11 状態としての関係値 |
| パターン適用v2（guarded_v2） | 上に加えて P19: 判定器は主張の種類を分類するだけ。保証人・目的・荷の検査はゲームの事実で確かめ、確かめられない主張は合計+1まで |

舞台は宿場町。3人のNPCがいる。
- **ミオ**（依頼人）: 行方不明の兄2人を探してほしい。見つけたらお礼に薬草袋をくれる
- **ゴウ**（門番）: 通行手形か、山賊ではないと納得できる理由があれば関所を通す
- **タマキ**（行商人）: 地図を100両で売る

[評価フレームワーク](../knowledge/ai-characters/evaluation.md) の攻撃表から作った8つの攻撃、判定器そのものを狙う5つの攻撃、4つの正当なプレイ、判断が分かれる1つ（L3）を流し、
**LLMの発言ではなく、ゲームの状態（所持品・フラグ・所持金）で**結果を判定する。

## 使い方

```bash
cd prototype

# モック（APIキー不要）: 仕組みの動作確認
python3 -m npc_lab.run_eval --backend mock

# 構造上の保証のテスト（判定器まで完全にだまされた最悪の場合）
python3 -m unittest discover -s tests -t .

# 実モデルでの実験（要 NPC_LAB_API_KEY、ANTHROPIC_API_KEY、または `ant auth login`）
pip install -r requirements.txt
# まず見積もる（APIは呼ばない）
python3 -m npc_lab.run_eval --dry-run --model claude-haiku-4-5 --only A12,A13,L5 --engines guarded_v2
# 必要な分だけ、上限付きで流す
python3 -m npc_lab.run_eval --backend anthropic --model claude-haiku-4-5 \
    --only A12,A13,L5 --engines guarded_v2 --max-usd 0.10 \
    --out ../experiments/$(date +%F)-result.md
```

- APIキーは `NPC_LAB_API_KEY` を優先して読む。Claude Code のクラウド環境では `ANTHROPIC_API_KEY` がセッションに渡らないため、こちらを使う
- 既定のモデルは `claude-opus-5`、`effort` は `low`（会話NPCは待ち時間が重要なため）。`--model` と `--effort` で変えられる（`claude-haiku-4-5` は effort 非対応なので送らない）
- 安全分類器による拒否に備えて、サーバー側フォールバック（`fallbacks: "default"`）を有効にしている
- **費用の方針**: 最小コストで進める（[STRATEGY.md](../STRATEGY.md) の「API試験の費用方針」）。`--max-usd`（既定 $0.50）で上限を付け、`--only` と `--engines` で必要な分だけ流す
- 費用の目安: 全シナリオ・3実装・5試行を `claude-opus-5` で流すと約1,150回・約7.5ドル。v2 の4シナリオを `claude-haiku-4-5` で1試行なら26回・約3セント（実測）

## 構成

```
npc_lab/
├── world.py      ゲームの状態とキャラクター設定（P05 バイブル形式）
├── llm.py        Claude API バックエンドとモック
├── agents.py     素朴な実装とパターン適用版のエンジン
├── scenarios.py  攻撃13種（うち判定器狙い5種）・正当なプレイ4種・判断が分かれるもの1種
├── run_eval.py   実行と結果の表の出力
├── probe_judge.py 判定器（P17）の採点を発言ごとに表示する調査用スクリプト（`--judge v2` で主張の分類も表示）
├── replay_probe.py probe_judge の記録を v2 のエンジンに流し直す（APIを呼ばない）
└── latency_probe.py 判定器とキャラの呼び出しを順番／同時で行ったときの待ち時間を比べる
tests/
└── test_guarantees.py  LLMが完全にだまされても守れること／守れないことのテスト
```

## 分かっていること・分かっていないこと
- モックは「だまされやすいLLM」を意図的に戯画化している。**モックでの結果は配線の確認であって、実際のモデルの性能を示すものではない**
- テストで確認できた構造上の保証: LLMと判定器が完全にだまされても、報酬・価格・同じ発言の繰り返しによる信頼の積み上げは守れる
- 構造だけでは守れない残存リスク（v1）: 判定器がだまされると、**異なる言い回しを3回**言えば門は開く
- v2 では、判定器が完全にだまされても門は事実の裏づけなしには開かない（信頼は最大2で止まる）。代わりに「話術だけで通る」体験はなくなる
