# pptx2jira — PowerPoint から Jira 課題を作る

PowerPoint（.pptx）の内容を、4つの段階で Jira の課題にする。Claude Code からは `/pptx-to-jira`（Markdown 化だけなら `/pptx-to-markdown`）で呼び出す。

```
.pptx ──①抽出──▶ slides.json / images/ / renders/ ──②vLLM──▶ deck.md ──③Claude──▶ issues.json ──検査──▶ ④Jira
          extract.py                              vlm_markdown.py        plan_issues.py      issues_schema.py   jira_push.py
                                                                       （既定は Claude Code 自身）
```

設計の検討と、各段階 3 回ずつのレビューの記録は [`REVIEW.md`](REVIEW.md)。

## 精度の考え方

1. **文字の正本は pptx のテキスト。** 画像からの文字起こし（OCR）は誤読するので、pptx に文字として入っているものは XML から直接取る。VLM には「この文字をそのまま使え」と渡す
2. **VLM は「見ないと分からないこと」だけに使う。** 読む順序・まとまり・矢印や流れ・図や写真の意味と、その中の文字
3. **表とグラフの値は VLM に書かせない。** VLM は表の位置に `{{TABLE-1}}` と置くだけで、中身は抽出した値で差し込む（桁や行のずれが起きない）
4. **出力は機械で検査する。** 原文の網羅率・原文にない数字・画像の説明の欠落を見て、不合格なら抜けを示して 1 回やり直させ、それでも駄目ならそのスライドは抽出結果を使う
5. **課題はすべて資料の引用（evidence）を持つ。** 引用が資料にない課題は「作り話の疑い」として登録前に止める
6. **登録は確認してから。** 既定は予定を出すだけ。`--apply` で初めて書き込み、二重登録はしない

## セットアップ

```bash
pip install -r tools/pptx2jira/requirements.txt
# スライド全体の画像を作るため（なくても動くが、VLM がレイアウトを見られない）
sudo apt-get install -y libreoffice-impress poppler-utils
```

vLLM（OpenAI 互換サーバー）で視覚言語モデルを動かしておく。例:

```bash
vllm serve Qwen/Qwen2.5-VL-7B-Instruct --max-model-len 32768 --limit-mm-per-prompt '{"image": 4}'
export VLLM_BASE_URL=http://localhost:8000/v1 VLLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
```

- 💡 日本語のスライドなら Qwen2.5-VL / Qwen3-VL 系が候補。7B で足りなければ 32B・72B。モデルの選定は自分の資料で `vlm_report.json` の網羅率と fallback の数を比べて決める
- `--limit-mm-per-prompt` の書き方は vLLM の版で違う【要確認: 使う版のドキュメント】。1 回に送る画像は「スライド全体 1 枚 + 埋め込み画像 `--max-images`（既定 3）枚」なので、上限は 4 以上にする
- 考える過程を出すモデル（Qwen3 の thinking など）は `--extra-body '{"chat_template_kwargs":{"enable_thinking":false}}'`

Jira の接続（値は表示・記録しない）:

| 環境 | 環境変数 |
|---|---|
| Jira Cloud | `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` |
| Jira Data Center / Server | `JIRA_BASE_URL`, `JIRA_PAT` |

Claude API（`plan_issues.py` を使う場合だけ）: `ANTHROPIC_API_KEY` か `ant auth login`。

## 使い方

```bash
T=tools/pptx2jira; W=p2j-work/資料名
python3 $T/extract.py 資料.pptx -o $W                       # ① 抽出
python3 $T/vlm_markdown.py $W --dry-run                      # ② 見積もり
python3 $T/vlm_markdown.py $W                                # ② Markdown 化 → $W/deck.md
python3 $T/plan_issues.py $W/deck.md --project-key PAY --dry-run   # ③ 費用の見積もり
python3 $T/plan_issues.py $W/deck.md --project-key PAY --model claude-haiku-4-5 --max-usd 0.2
python3 $T/issues_schema.py $W/issues.json --deck $W/deck.md --fix # 検査
python3 $T/jira_push.py $W/issues.json --offline             # ④ 作る予定（接続なし）
python3 $T/jira_push.py $W/issues.json                       # ④ 事前確認（接続あり、書き込まない）
python3 $T/jira_push.py $W/issues.json --apply --attach-renders $W   # ④ 登録
```

`p2j-work/` は `.gitignore` 済み（資料の中身をリポジトリに入れない）。

## 各段階のアルゴリズム

### ① 抽出（extract.py）

| 対象 | やり方 |
|---|---|
| 読む順序 | 再帰 XY-cut。図形の外接矩形の影が途切れる帯を上下・左右で探し、**実際の幅で広い方**で切る。(top, left) の並べ替えだけだと 2 段組みを交互に読む |
| グループ図形 | 子の座標を、グループの `chOff/chExt → off/ext` で変換してスライド座標に直す（入れ子は合成） |
| 箇条書き | 段落 XML の `lvl`・`buChar`・`buAutoNum`・`buNone`。本文プレースホルダは記号の指定がなくても箇条書き。番号は階層ごとに数え、親が進めば子を振り直す |
| 太字・リンク | ラン単位で `**…**`、`[…](URL)`。行頭が `#` や `1.` の普通の文はエスケープ |
| 表 | 結合セルは起点の値を結合範囲に繰り返す（行ごとに読んだとき「実装の担当」が空にならない）。結合の範囲は `merged` に残す |
| グラフ | 種類・題・分類・系列の値（chart XML の値） |
| SmartArt | データ部（`dgm:dataModel`）の点と `parOf` の接続をたどって、順序と階層つきの項目にする |
| 画像 | 内容のハッシュで重複を除いて保存。スライド面積の 0.4% 未満・40px 未満、半数以上のスライドに出るもの（ロゴ）は装飾扱い。代替テキストも取る |
| ノート | 発表者ノートは原文のまま（VLM に通さない。担当・期限が書かれやすい） |
| タイトル | タイトルのプレースホルダ。なければ上 20% の 1 段落・60 字以下の文字の箱を題とみなす（`title_guessed`） |
| 除外 | スライド番号・日付・フッター。非表示スライドは既定で Markdown に入れない |
| スライド画像 | LibreOffice で PDF（非表示スライドも出す）→ `pdftoppm` で PNG。ページ数とスライド数を突き合わせる |

### ② Markdown 化（vlm_markdown.py）

- 入力: 原文の JSON（座標を除いた文字と構造）+ スライド全体の画像 + 大きい順に埋め込み画像（長辺 1600px に縮小）
- 指示: 原文の文字は一字一句そのまま / 表とグラフは `{{TABLE-n}}` `{{CHART-n}}` の行だけ / 埋め込み画像は `> 図（IMG-n）: ` で説明 / 読めない文字は【要確認】/ 原文と画像にないことを書かない
- 後処理: `<think>` とコードフェンスを除く、タイトルの見出しを除く、`#`・`##` を `###` に下げる、表とグラフを差し込む（置き忘れは末尾に足す）
- 検査（合格の条件）: 本文の網羅率 ≥ 0.95（文字数で重み付け、NFKC・記号・空白の差を無視、6 字以上はあいまい一致）、図の説明の外に原文にない 2 桁以上の数字がない、送った画像すべてに説明がある
- 不合格: 抜け・作られた数字・説明のない画像を示して 1 回やり直し。合格した試行を優先して採用。全部不合格なら、抽出結果の Markdown + いちばん長い図の説明（`fallback`）
- その他: 温度 0、同時 4 本、429/5xx は指数バックオフ、入力のハッシュでキャッシュ、1 枚の失敗で全体を止めない（`error_fallback`）、画像のないスライドは VLM を呼ばない（`text_only`）

### ③ 課題の計画（Claude）

- 指示は [`prompts/plan_issues.md`](prompts/plan_issues.md)。Claude Code のスキルでも `plan_issues.py` でも同じものを使う
- 構造: エピック → 課題（story / task / bug）→ サブタスク、依存（depends_on）、未解決の問い（open_questions）、除外したスライドと理由（skipped_slides）
- 推測を見える化: 資料にない項目は空にする。補ったら `inferred_fields` に書く。担当は資料の表記のまま（Jira のユーザーには割り当てない）
- `plan_issues.py`: 構造化出力（JSON スキーマ）、指示と資料をキャッシュ、呼ぶ前に `count_tokens` で費用を見積もって `--max-usd` で止める、`--review-pass` で資料と突き合わせて直す 2 回目、拒否時の server-side fallback（対応モデルのみ）
- 既定のモデルは `claude-opus-5-5`。試すときは `--model claude-haiku-4-5` から（リポジトリの費用方針）

### 検査（issues_schema.py）

| 種類 | 内容 |
|---|---|
| エラー（登録を止める） | スキーマ違反、ref の重複、根拠の引用が資料にない、出典のスライドがない、依存先がない・自己依存・循環、要約が空・255 字超・改行あり、ラベルに空白や記号、期限が日付でない |
| 警告（人が判断） | 引用が出典とは別のスライドにある、要約・受け入れ条件の数字が出典にない、推測でない期限の数字が資料にない、担当の表記が出典にない、要約がほぼ同じ課題、どの課題にも使われず除外理由もないスライド |
| 自動の直し（`--fix`） | ラベルの空白・記号、要約の改行と空白、重複ラベル |

### ④ Jira 登録（jira_push.py）

- REST の版: `serverInfo` の `deploymentType` が Cloud なら v3（説明は ADF）、それ以外は v2（Wiki 記法）
- 課題タイプ: 名前（英語・日本語）→ 階層（`hierarchyLevel`、`subtask`）の順で対応づけ。story・bug がなければ task。`--type-map` で上書き
- 事前確認: 自分のアカウント、プロジェクト、タイプごとの作成画面の項目（createmeta）。埋められない必須項目は警告、必要なタイプがなければ書き込む前に止める
- 親子: Cloud は `parent`。Data Center はエピックに Epic Name、子に Epic Link（項目があれば）。サブタスクは `parent`
- 項目: 要約、説明（本文 + 受け入れ条件 + 担当の表記 + 推測した項目 + 出典と引用）、ラベル（課題のラベル + `pptx2jira` + 資料ごとの `p2j-<ハッシュ>`）、優先度（プロジェクトにあれば）、期限
- 二重登録の防止: 作るたびに `jira_state.json` に ref → キーを保存。状態ファイルがなくても資料のラベルで検索して、要約とタイプが同じ課題を拾い直す。依存のリンクも既存を確かめてから作る
- 失敗の扱い: 429 は Retry-After、5xx・接続エラーは指数バックオフ。親が作れなかった子は作らない。途中で止まっても同じコマンドで続きから
- `--attach-renders`: 出典スライドの画像（最大 3 枚）を課題に添付

## 出力ファイル（作業ディレクトリ）

| ファイル | 中身 |
|---|---|
| `slides.json` | 抽出結果（スライドごとの構造、`text_units` は網羅率の単位） |
| `extracted.md` | 抽出結果だけの Markdown（VLM なしの基準） |
| `images/`, `renders/` | 埋め込み画像、スライド全体の画像 |
| `md/slide-NNN.md`, `deck.md` | VLM で整えた本文、全体（段階③の入力） |
| `vlm_report.json` | スライドごとの状態・網羅率・抜け・作られた数字・説明のない画像 |
| `issues.json` | 課題の計画（`plan` がスキーマ本体） |
| `jira_state.json` | 登録済みの ref → キー、作ったリンク |

## テスト

```bash
cd tools/pptx2jira && python3 -m unittest discover -s tests -v
```

外部サービスは使わない。崩れやすい要素を詰めたサンプルの pptx（`tests/make_sample.py`）と、偽の vLLM・Jira（`tests/mock_servers.py`）で、全段階を確かめる。偽 vLLM は「理想の VLM」を戯画化したもので、実際のモデルの精度は示さない。

## 分かっていないこと・限界

- 実際の vLLM のモデルと実際の Jira では、まだ試していない（このリポジトリの環境に両方がないため）。最初の実行では `vlm_report.json` と `--offline` / 事前確認の出力をよく見る
- 網羅率は「原文の文字が残っているか」で、並びや階層の正しさは測れない。fallback のスライドと図の多いスライドは目で確かめる
- 画像の中の文字（スクリーンショットなど）は VLM の読み取りに頼る。数字の検査は図の説明の中を対象外にしているので、誤読は検出できない
- `.ppt`（古い形式）、埋め込みの Excel・動画の中身、数式（OMML）は取り出さない
- 担当者の自動割り当て、スプリント・ストーリーポイントの設定はしない
