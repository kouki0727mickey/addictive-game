# CLAUDE.md — AI × エンタメ ナレッジベース

このリポジトリは「AI × エンターテイメント」のナレッジベース。ゲームを中心に、企画・制作・公開の判断に使う。
ユーザーとは日本語で話す。

## ナレッジの場所
- 入口: `knowledge/00_landscape.md`（全体マップ）、`README.md`（構成と運用ルール）
- ゲーム制作でまず読む記事:
  - `knowledge/foundations/engagement-design.md` — 「ハマる」の設計と、健全・不健全の判定（レッドライン）
  - `knowledge/domains/games.md` — ゲームでのAI活用、Steamの開示ルール、LLM NPCのチェックリスト
  - `knowledge/foundations/ai-native-entertainment.md` — AIでしか成立しない体験の設計原則
  - `knowledge/business/business-models.md` — 収益モデルとコスト構造
- AIキャラクター・会話NPC: `knowledge/ai-characters/`（38パターン、事例14件、評価、説得NPCの実践ガイド）
- 開示と法務: `knowledge/foundations/ai-disclosure-guide.md`、`knowledge/ethics-legal/by-country/`
- 実験環境: `prototype/`（会話NPCの堅牢性）、記録は `experiments/`

別のリポジトリで作業していて `knowledge/` が手元にない場合は、公開リポジトリを読み込み用に取得する:
`git clone --depth 1 https://github.com/kouki0727mickey/addictive-game /tmp/ai-ent-kb`（読むのは `/tmp/ai-ent-kb/knowledge/`）。

## スキル（ゲーム制作用）
| スキル | 使う場面 |
|---|---|
| `/game-concept` | AIを使ったゲーム（または既存ゲームへのAI機能）の企画書を作る |
| `/game-ai-character` | 会話NPC・AIキャラクターを設計する |
| `/game-release-check` | 公開前に、健全性・AI開示・国別法務・ストア規約を点検する |

## 作業ルール
1. **企画・設計の前に、関連する記事を読む。** 提案には根拠にした記事やパターン番号（例: P16、事例 F02）を添える
2. **事実と仮説を分ける。** 事実（数字・日付・企業動向・法令）には出典を付ける。ナレッジにない新しい事実は、調べて出典を付けるか `【要確認】` とする。意見・仮説は 💡 を付ける
3. **レッドラインを越える設計は提案しない**（`engagement-design.md` の「レッドライン」）。依頼がそれに当たる場合は、理由と代わりの設計を示す
4. **法務は一般的な情報整理であり、法的助言ではない**と明記する。国・ストアの要件は `by-country/` と `games.md` の日付を確認し、古い可能性があれば一次情報で確かめる
5. **API費用は最小に。** Claude API を呼ぶ実験は、実行前に `--dry-run` で見積もり、安いモデル（`claude-haiku-4-5`）から、`--max-usd` を付けて流す（`STRATEGY.md` の「API試験の費用方針」）。APIキーは表示・記録しない
6. **制作物の置き場所**: このリポジトリで作るゲームの企画書・設計書・点検結果は `studio/<プロジェクト名>/` に置く。ゲーム本体のリポジトリで作業している場合は、そのリポジトリの `docs/ai-design/` に置く

## 成果をナレッジに戻す
制作で分かったこと（うまくいった設計、失敗、プレイヤーの反応、実測したコスト）は、ナレッジに戻す。
- 新しい事例 → `knowledge/ai-characters/case-studies.md` または `knowledge/domains/case-studies.md`
- 新しい設計パターン・既存パターンの修正 → `knowledge/ai-characters/patterns.md`
- 自前の検証 → `experiments/YYYY-MM-DD-<名前>.md`
- 戻すときは `templates/knowledge-entry.md` の書式と上の作業ルールに従い、英語版（`knowledge/en/`）がある記事は英語版も直す
- 変更後は相対リンクのリンク切れ検査と `python tools/build_site.py && mkdocs build` を通す。main への反映は PR で行う（マージするとサイトに公開される）
