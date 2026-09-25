# addictive-game

> English: the focus area on AI characters and conversational NPCs is available in English at [knowledge/en/ai-characters](knowledge/en/ai-characters/README.md).

**AI × エンターテイメントの世界一のナレッジベース**を目指すリポジトリ。

ゲーム・映像・音楽・アニメ・ライブ・インタラクティブ物語など、エンタメのあらゆる領域で
「AIが何を変えるのか／どう作り・どう稼ぎ・どう守るのか」を、体系的・実践的・継続更新型でまとめる。

## 何をもって「世界一」とするか

| 軸 | 定義 | 測り方 |
|---|---|---|
| 網羅性 | エンタメ全領域 × AI技術 × ビジネス × 法務・倫理をカバー | 分類マップ上の空白セル数 |
| 深さ | 「概要」で終わらず、設計パターン・失敗事例・実装手順まで書く | 各記事の成熟度レベル（L1〜L4） |
| 鮮度 | 変化の速い分野なので、全記事に最終確認日を持つ | 90日以上未更新の記事数 |
| 実践性 | 読んだ人がそのまま企画・開発・判断に使える | チェックリスト/テンプレート数 |
| 独自性 | 他所の要約ではなく、自分たちの検証・仮説・プロトタイプを含む | 一次情報（実験ログ）の数 |

詳細な戦略は [`STRATEGY.md`](STRATEGY.md) を参照。

## 構成

```
knowledge/
├── 00_landscape.md            全体マップ（まずここから）
├── foundations/               横断的な基礎
│   ├── tech-stack.md          エンタメで使うAI技術の地図
│   ├── engagement-design.md   「ハマる」の科学とAI（本リポジトリの核）
│   ├── ai-native-entertainment.md  AIネイティブなエンタメの設計原則
│   └── ai-disclosure-guide.md  実践ガイド: 作品でのAI利用の開示（事例44件から）
├── ai-characters/             ★重点領域: AIキャラクター・会話NPC
│   ├── patterns.md            設計パターン集（38パターン）
│   ├── case-studies.md        事例分析（14件）
│   ├── evaluation.md          評価フレームワークとリリース判定
│   └── playbook-persuasion-npc.md  実践ガイド: 説得をゲームにする会話NPC（自前の実験に基づく）
├── domains/                   領域別
│   ├── games.md
│   ├── film-video.md
│   ├── music.md
│   ├── anime-manga.md
│   ├── characters-vtuber-live.md
│   ├── interactive-story.md
│   └── case-studies.md        映像・音楽・アニメ/マンガの事例分析（30件）
├── business/
│   └── business-models.md     収益モデル・コスト構造・参入戦略
├── ethics-legal/
│   ├── ethics-legal.md        著作権・肖像/声・依存性・透明性（論点別）
│   └── by-country/            国別（日本・米国・EU・中国・韓国）と比較表
├── en/                        英語版（English edition）: ai-characters, foundations/ai-disclosure-guide
├── glossary.md                用語集
└── _verification-log.md       事実確認ログ
templates/
└── knowledge-entry.md         新規記事テンプレート
prototype/                     会話NPCの堅牢性を測る実験環境（Python）
experiments/                   実験記録（一次情報）
```

## 成熟度レベル

各記事の冒頭に記載する。

- **L1 概観**: 主要トピックと用語が整理されている
- **L2 構造化**: パターン・分類・判断基準が書かれている
- **L3 実践**: 事例分析・チェックリスト・手順がある
- **L4 独自知見**: 自前の実験・プロトタイプ・データに基づく知見がある

## 運用ルール

1. 新規記事は [`templates/knowledge-entry.md`](templates/knowledge-entry.md) から作る
2. 事実（数字・日付・企業動向）には出典URLと確認日を付ける。未確認なら `【要確認】` を付ける
3. 意見・仮説は `💡仮説:` と明示し、事実と混ぜない
4. 記事のfrontmatterの `last_reviewed` を更新時に書き換える
