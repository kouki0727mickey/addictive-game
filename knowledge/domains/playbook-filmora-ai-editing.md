---
title: 実践ガイド: Filmora と Claude をつないで高品質の動画を作る
domain: film-video
maturity: L2
last_reviewed: 2026-09-25
tags: [film, video-editing, filmora, workflow, automation, mcp, disclosure]
---

# 実践ガイド: Filmora と Claude をつないで高品質の動画を作る

> 関連: [映像 × AI](film-video.md) ／ [実践ガイド: AI利用の開示](../foundations/ai-disclosure-guide.md) ／ [ビジネスモデル（コスト構造）](../business/business-models.md)

## 一言で言うと
2026年9月時点で、**Filmora を外から直接操作する公式の API や MCP サーバーはない**[^nomcp]。
そのため「つなぐ」は、**Claude が設計図（台本・構成表・字幕・指示文）を作り、Filmora が組み立てる**分業で行うのが現実的。
タイムラインまでプログラムで操作したいなら、スクリプト API と MCP サーバーがそろう DaVinci Resolve の方が向いている[^resolve]。

## なぜ重要か
- 動画の品質は「編集ソフトの機能」より、**企画・構成・音・字幕の設計**で決まる部分が大きい。ここは Claude が得意な領域
- 一方で Filmora は AI 機能（字幕生成、ノイズ除去、生成動画、AI Mate）が充実しており[^v15][^v16]、組み立てと仕上げの速度が出る
- 接続方法を間違えると、非公式ツールで**プロジェクトが壊れる**、**マルウェアを入れる**、**AIクレジットを浪費する**といった事故が起きる

## Filmora の現状（2026-09-25 確認）

| 項目 | 内容 | 出典 |
|---|---|---|
| 最新版 | 16.0.9（2026-09-24 更新、Windows / macOS）。v16 の新機能: AI Eye Contact、AI Video Enhancer（4K アップスケール）、字幕の30言語以上への翻訳、Idea to Video Agent、HDR カラーホイール、ウィンドウ録画 | [^v16] |
| AI Mate（v15〜） | 編集アシスタント。**Action**（複数手順の編集を自動実行: フック/エンド画面の生成、音声ノイズ除去、フリーズフレーム等）、**Guide**（機能の場所へ案内）、**AIGC**（テキスト/画像から動画・音楽を生成、プロンプト最大500字）、**Inspiration to Video Agent**（素材探し・シーン配置・動き・吹替までの半自動制作） | [^aimate] |
| 字幕 | 音声からの自動字幕（SRT 出力可）、SRT の読み込み・編集・書き出し、TTS（自分の声を学習する Voice Modeling あり） | [^stt][^srt] |
| 外部 API | **なし（タイムライン操作用）**。Wondershare AILab API は画像・音声・動画の個別 AI 処理（背景除去、ボーカル除去、ノイズ除去、動画の背景除去など）を REST で呼べるが、Filmora のプロジェクトは開けない | [^ailab][^nomcp] |
| MCP サーバー | 公式なし。コミュニティのリポジトリも中身が空（2026-09-21 時点） | [^nomcp] |
| プロジェクトファイル | `.wfp` は非公開形式（圧縮アーカイブ）。非公式の Python ツール automate-filmora（MIT）が一部の編集に対応 | [^automate] |
| 料金 | Free（書き出しに透かし）/ Basic $49.99/年（AI は従量課金、AI Mate 会話500回）/ Advanced $59.99/年（AIクレジット1,000/月、未使用分は翌期に失効）/ 買い切り $79.99（AIクレジット1,000は1回限り、更新は v16 内のみ）。価格は割引表示時のもの | [^price] |

## 接続の方法（5通り）

| # | 方法 | できること | 品質・安定性 | 推奨度 |
|---|---|---|---|---|
| A | **ファイル受け渡し** | Claude が台本、ショットリスト、SRT 字幕、ナレーション原稿、BGM/SE の指定を作り、Filmora に読み込む | 高い。Filmora の正規機能だけを使う | ◎ 基本はこれ |
| B | **AI Mate へのプロンプト受け渡し** | Claude が AI Mate 用の指示文（500字以内）を作り、貼り付けて Action/AIGC を実行 | 中。結果は AI Mate 次第、クレジットを消費 | ○ 定型作業の時短に |
| C | **`.wfp` の直接編集**（automate-filmora） | 既存プロジェクトの解析、タイトル文字の差し替え、位置・拡大率、音量・フェード、ディゾルブ、無音カットのラフ編集 | 低〜中。検証は macOS の 15.6.4〜15.7.11 のみ。**v16 と Windows は未検証** | △ 量産テンプレートの差し替えに限定 |
| D | **画面操作**（Claude の computer use） | Filmora の画面をクリック・入力で操作 | 低。遅く、UI 変更で壊れる | △ 最終手段 |
| E | **AILab API** | 素材の前処理（背景除去、ボーカル分離、ノイズ除去）をバッチで実行し、結果を Filmora に読み込む | 中。バックエンドから呼ぶ必要あり、従量課金 | ○ 大量素材の前処理に |

💡 **推奨構成**: A を軸に、素材の前処理（音量の正規化・書き出し形式の統一・無音検出）は FFmpeg などの自前スクリプトで行い、Filmora では「組み立て・見た目・最終書き出し」に集中する。C は同じ型の動画を大量に作るときだけ検討する。

### C（`.wfp` 直接編集）を使うときの注意
automate-filmora 自体が次の安全策を前提にしている[^automate]。
- 元ファイルは読み取り専用。編集は**別名のコピー**に出力し、既存ファイルは上書きしない
- 編集は入力ファイルの SHA-256 に紐づけ、構造監査に失敗した出力は自動で消す
- **作ったコピーは、テンプレートを作ったのと同じ Filmora のビルドで開いて保存し、閉じてもう一度開いて確認してから使う**
- Filmora の更新で形式が変わる可能性がある。💡 本番案件ではバージョンを固定し、自動更新を止めてから使う

## 高品質にするための工程（Claude と Filmora の分担）

| 工程 | Claude がやること | Filmora でやること | 品質の基準 |
|---|---|---|---|
| 1. 企画 | 目的・視聴者・尺・「最初の3秒」の案、競合との差分 | — | 1文で言える主題がある |
| 2. 台本・構成 | 台本、シーン表（尺・映像・テロップ・音）、ショットリスト | — | シーンごとに役割（掴む・説明・証拠・行動喚起）が決まっている |
| 3. 素材 | 撮影リスト、不足素材の洗い出し、生成素材のプロンプト | 素材の読み込み、AI 生成（AIGC）、AI Video Enhancer | 解像度とフレームレートをそろえる |
| 4. 粗編集 | シーン表に沿った並びの指示、AI Mate 用の指示文 | 並べる、無音カット、Smart Short Clips など | 尺が企画の ±10% 以内（💡目安） |
| 5. 音 | ナレーション原稿、BGM/SE の指定 | ノイズ除去、音量調整、TTS | 完成版を実測する。YouTube 向けは統合ラウドネス −14 LUFS・トゥルーピーク −1 dBTP 以下が通説[^lufs]（YouTube 公式の数値ではない【要確認】） |
| 6. 字幕 | 読みやすく整えた SRT（1行の文字数、改行位置、用語の統一）、翻訳 | SRT 読み込み、スタイル設定、ダイナミック字幕 | 誤字ゼロ、表示時間が読める長さ |
| 7. 色・見た目 | ルックの方針（参考作品、トーン） | カラー調整（v16 は HDR カラーホイール）、タイトル、トランジション | ショット間で色と明るさが揃っている |
| 8. 書き出し | 配信先ごとの設定表 | 書き出し | プロジェクトと同じフレームレート。4K の H.264/H.265 は 35〜45 Mbps 程度が目安とされる[^export]【要確認】 |
| 9. 点検 | チェックリストで見直し（下記） | 通しで再生 | 下のチェックリストを全部満たす |

### Claude に渡すと効くもの
- **シーン表の形式を固定する**（例: `#, 開始, 尺, 映像, テロップ, ナレーション, 音, 備考`）。Filmora で組むときの手順書になる
- **SRT は Claude に直接書かせず、Filmora の自動字幕（または Whisper 等）で作った SRT を Claude に校正させる**。タイムコードは音声から取る方が正確（💡）
- AI Mate への指示は、1回に1つの作業・対象クリップ・望む結果を明記する（💡）

## コストの考え方
- AI 機能は AI クレジットを消費する。10分の動画の背景除去で 200〜300 クレジットを使うという報告がある[^credits]【要確認】。Advanced の月1,000 クレジットは数本で尽きうる
- 💡 高くつく処理（背景除去、生成動画、アップスケール）は**完成に近い段階で、使う区間だけ**にかける。試行錯誤は低解像度・短い区間で行う
- Claude API を使う場合は、このリポジトリの方針（`--dry-run` で見積もり、安いモデルから、上限付き）に従う（[STRATEGY.md](../../STRATEGY.md)）

## 落とし穴・リスク
- **非公式の「自動化」「アクティベーター」配布物**: 検索すると Filmora の有料機能を解除すると称する GitHub リポジトリが出てくる。ライセンス違反であり、マルウェアの危険もある。使わない
- **AI 開示**: YouTube は、実在の人物・場所・出来事と見間違えるリアルな合成・改変（生成 AI を含む）に開示を求める。台本作成・字幕の自動生成など制作補助は対象外。開示しないことが続くと、ラベルの強制付与や収益化停止の可能性がある[^yt]。開示の考え方は [実践ガイド: AI利用の開示](../foundations/ai-disclosure-guide.md) を参照
- **声と肖像**: Voice Modeling で学習させるのは**本人の声だけ**にする。他人の声・顔の生成は国ごとの規制がある（[国別比較](../ethics-legal/by-country/README.md)）。法務の記述は一般的な情報整理であり、法的助言ではない
- **生成素材の権利**: 生成動画・音楽の商用利用条件は Filmora の利用規約とモデル提供元の条件の両方を確認する【要確認】
- **バージョン依存**: AI Mate の機能や `.wfp` の形式は更新で変わる。手順書には Filmora のバージョンを書く

## 実践チェックリスト
- [ ] 接続方法を A〜E から選び、理由を書いた（基本は A）
- [ ] シーン表・台本を Claude で作り、主題が1文で言える
- [ ] 素材の解像度・フレームレートがプロジェクト設定とそろっている
- [ ] 完成版の音量を実測した（配信先の基準に合わせた）
- [ ] 字幕を校正した（誤字、1行の長さ、表示時間、用語の統一）
- [ ] ショット間で色・明るさがそろっている
- [ ] 書き出し設定を配信先ごとに確認した
- [ ] リアルな合成・改変があれば、配信先で AI 利用を開示した
- [ ] 他人の声・顔・素材を無断で使っていない
- [ ] 使った AI クレジットと Claude API の費用を記録した（ナレッジに戻す）

## 未解決の問い / 💡仮説
- 💡 Wondershare が MCP サーバーまたはタイムライン API を公開すれば、方法 A〜D は不要になる。公開状況を定期的に確認する
- 💡 Filmora 16 の Idea to Video Agent と Claude の台本を組み合わせたとき、手作業との品質差・時間差はどれくらいか（未検証。検証したら `experiments/` に記録する）
- automate-filmora が Filmora 16 のプロジェクトで動くか（未検証）

## 参考文献
[^nomcp]: AITuber「Wondershare Filmora MCP for Claude: Does It Exist?」https://aituber.app/blog/filmora-mcp/ （2026-09-21 時点の調査。自社製品の宣伝を含む記事なので、結論のみ採用。確認日: 2026-09-25）
[^resolve]: GitHub「samuelgursky/davinci-resolve-mcp」（Resolve 21 のスクリプト API 用 MCP）https://www.claudedirectory.org/mcp-servers/samuelgursky-davinci-resolve-mcp ／「lordhoell/davinci-resolve-mcp」https://github.com/lordhoell/davinci-resolve-mcp ／「emircbngl/davinci-resolve-mcp-free」（無償版向け）https://github.com/emircbngl/davinci-resolve-mcp-free 。フル機能のスクリプト API は有償の Studio 版が必要（確認日: 2026-09-25）
[^v15]: Gizmodo「AI Mate in Wondershare Filmora V15」https://gizmodo.com/ai-mate-in-wondershare-filmora-v15-a-new-era-of-intelligent-video-creation-2000700107 ／ Wikipedia「Wondershare Filmora」https://en.wikipedia.org/wiki/Wondershare_Filmora （確認日: 2026-09-25）
[^v16]: TechSpot「Wondershare Filmora Download - 16.0.9」https://www.techspot.com/downloads/7462-wondershare-filmora.html （確認日: 2026-09-25）
[^aimate]: Wondershare「AI Mate Editing for Windows」https://filmora.wondershare.com/guide/ai-copilot-editing.html （確認日: 2026-09-25）
[^stt]: Wondershare「STT/TTS/SRT Feature」https://filmora.wondershare.com/guide/stt-tts-srt.html （確認日: 2026-09-25）
[^srt]: Wondershare「How to Add Subtitles & AI Captions in Filmora」https://filmora.wondershare.com/video-editing-tips/how-to-add-subtitles.html （確認日: 2026-09-25）
[^ailab]: Wondershare AILab API Documentation「Product Introduction」https://ailab.wondershare.com/doc/guide/Introduction.html ／「Obtain Request Credentials」https://ailab.wondershare.com/doc/start/GetAPIKEY.html （確認日: 2026-09-25）
[^automate]: GitHub「mikecann/automate-filmora」https://github.com/mikecann/automate-filmora （MIT、確認日: 2026-09-25）
[^price]: Wondershare「Filmora Pricing & Plans」https://filmora.wondershare.com/shop/buy/buy-video-editor.html （地域・時期で価格が変わる。確認日: 2026-09-25）
[^credits]: CostBench「Filmora Hidden Costs」https://costbench.com/software/video-editing/filmora/hidden-costs/ （第三者の報告。確認日: 2026-09-25）
[^lufs]: Audio Forge Pro「YouTube LUFS Target」https://audioforgepro.com/blog/youtube-lufs-normalization-guide ／ Wikipedia「Audio normalization」https://en.wikipedia.org/wiki/Audio_normalization （第三者の解説。確認日: 2026-09-25）
[^export]: Wondershare「Best Export Settings for Premiere Pro vs. Filmora V15」https://filmora.wondershare.com/basic-video-editing/best-export-settings-for-premiere-pro.html ／ Filmora.TV の書き出し上限（4K・60fps・50Mbps）https://support.wondershare.com/how-tos/filmora-tv/supported-export-formats-resolution-framerate-bitrate.html （確認日: 2026-09-25）
[^yt]: YouTube Help「Disclosing use of altered or synthetic content」https://support.google.com/youtube/answer/14328491 ／ YouTube Blog「How we're helping creators disclose altered or synthetic content」https://blog.youtube/news-and-events/disclosing-ai-generated-content/ （確認日: 2026-09-25）
