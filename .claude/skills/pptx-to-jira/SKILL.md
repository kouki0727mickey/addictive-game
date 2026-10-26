---
name: pptx-to-jira
description: PowerPoint（.pptx）の内容を、テキスト・画像の抽出 → vLLM の視覚言語モデルで Markdown 化 → Claude が Jira 課題（エピック・ストーリー・タスク・サブタスク・依存）に整理 → 検査 → Jira に登録、の順で取り込む。「パワポからJiraチケットを作りたい」「スライドの要件を課題にしたい」「pptxをJiraに登録」と言われたときに使う。
---

# PowerPoint から Jira 課題を作る

道具は `tools/pptx2jira/`（説明は同じ場所の `README.md`、各段階の中身の動きは `HOW_IT_WORKS.md`、設計の検討とレビューの記録は `REVIEW.md`）。
このリポジトリにない場合は `git clone --depth 1 https://github.com/kouki0727mickey/addictive-game /tmp/ai-ent-kb` して `/tmp/ai-ent-kb/tools/pptx2jira/` を使う。
以下 `T=tools/pptx2jira`、作業ディレクトリ `W=p2j-work/<資料名>`（`.gitignore` 済み。資料の中身をコミットしない）。

精度の考え方: **文字の正本は pptx から機械的に抜いたテキスト**。VLM は並び・図・矢印を読むためだけに使い、出力は網羅率と数字で検査する。課題はすべて資料の引用（evidence）を持ち、引用が資料にないものは登録前に止める。

## 0. 確かめること（ユーザーに聞く）
- pptx のパス、Jira のプロジェクトキー
- vLLM のエンドポイントとモデル（環境変数 `VLLM_BASE_URL`, `VLLM_MODEL`。なければ手順2を飛ばす）
- Jira の接続情報が環境変数にあるか（`JIRA_BASE_URL` と、`JIRA_EMAIL`+`JIRA_API_TOKEN` または `JIRA_PAT`）。**値は表示・記録しない**。`[ -n "$JIRA_API_TOKEN" ]` のように有無だけ見る
- `.ppt`（古い形式）なら、先に `soffice --headless --convert-to pptx` で変換する

依存: `pip install -r $T/requirements.txt`。スライド画像には LibreOffice（`soffice`）と `pdftoppm` を使う（なくても動くが VLM の精度が落ちる）。

## 1. 抽出
```bash
python3 $T/extract.py <資料.pptx> -o $W
```
- 出力の `warnings` を見る。ページ数とスライド数が合わない、などがあればユーザーに伝える
- 非表示スライドは既定で除外。含めるなら `--include-hidden`

## 2. Markdown 化（vLLM）
```bash
python3 $T/vlm_markdown.py $W --dry-run          # 呼び出し回数と送る画像の数
python3 $T/vlm_markdown.py $W                    # 本番（VLLM_BASE_URL / VLLM_MODEL を使う）
```
- 結果の `status` を見る: `vlm`（そのまま合格）/ `vlm_retry`（やり直しで合格）/ `fallback`（VLM が文字を落としたので抽出結果を使った）/ `error_fallback`（VLM の呼び出しに失敗）
- `fallback`・`error_fallback` のスライドと、`$W/vlm_report.json` で `invented_numbers` か `missing_figures` が空でないスライドは、`$W/renders/slide-NNN.png` を Read で開いて自分の目で確かめる。図や矢印の意味が落ちていれば `$W/md/slide-NNN.md` を直し、`python3 $T/vlm_markdown.py $W --rebuild-deck` で deck.md だけ作り直す（VLM は呼ばない）
- 全スライドが `error_fallback` なら vLLM に届いていない。`VLLM_BASE_URL` とサーバーの状態を確かめる
- vLLM がないとき: `cp $W/extracted.md $W/deck.md` として進める。図が重要なスライドは、render の PNG を Read で見て、`> 図: ` の説明を deck.md に直接書き足す（Claude Code 自身が VLM の代わりをする。この場合は `--rebuild-deck` を使わない。書き足した分が消える）
- Qwen3 系など考える過程を出すモデルは `--extra-body '{"chat_template_kwargs":{"enable_thinking":false}}'`

## 3. 課題の計画（Claude）
**既定は、このセッションの Claude（あなた）が作る**（API 費用がかからない）。
1. `$T/prompts/plan_issues.md` を読み、その指示に従う
2. `$W/deck.md` を全部読む（長ければ分けて読むが、全スライドを読み終えてから書く）
3. `python3 $T/issues_schema.py --print-schema` でスキーマを確かめ、次の形で `$W/issues.json` を書く:
   `{"version": 1, "source": {"file": <deck.md 1行目の # の後>, "sha256": <deck.md の source-sha256>}, "project_key": "<キー>", "plan": {<スキーマに従う>}}`
4. 自分で見直す（次の観点で1件ずつ。直したら `review_notes` に書く）:
   表の各行・発表者ノートの担当と期限の取りこぼし / 資料にない作業・数値・日付・人名の混入 / evidence が資料の文と一字一句一致しているか / 重複・粒度・type / 推測した項目が `inferred_fields` に入っているか

大量の資料を一括で流すときや CI では、代わりに API を使う:
```bash
python3 $T/plan_issues.py $W/deck.md --project-key <キー> --dry-run --model claude-haiku-4-5   # 費用の見積もり
python3 $T/plan_issues.py $W/deck.md --project-key <キー> --model claude-haiku-4-5 --max-usd 0.2   # まず安いモデルで
```
精度を上げるなら既定のモデル（`claude-opus-5-5`）と `--review-pass`。API キーは表示しない。キーがなければ、このセッションで作る方に戻る。

## 4. 検査
```bash
python3 $T/issues_schema.py $W/issues.json --deck $W/deck.md --fix
```
- `errors` が 0 になるまで issues.json を直す（特に「根拠が資料にない（作り話の疑い）」は、課題を消すか evidence を資料の文に合わせる）
- `warnings`（取りこぼしの疑い、期限の数字が資料にない、担当が見当たらない、重複の疑い）は一つずつ判断し、直さないものは理由をユーザーに伝える

## 5. 確認してから登録
1. `python3 $T/jira_push.py $W/issues.json --offline` で作る予定の一覧を出す
2. 接続情報があれば `python3 $T/jira_push.py $W/issues.json` で事前確認（課題タイプの対応・必須項目・作る内容。まだ書き込まない）
3. ユーザーに、エピックと課題の一覧（ref・タイプ・要約・期限・担当の表記）、`open_questions`、推測した項目、検査の警告を表で見せ、**登録してよいか明示的に確認する**。Jira への登録は他の人にも見える外向きの操作で、取り消しが面倒
4. 了承を得たら:
```bash
python3 $T/jira_push.py $W/issues.json --apply --attach-renders $W
```
- 再実行しても二重には作らない（`$W/jira_state.json` と資料ごとのラベル `p2j-<ハッシュ>`）。途中で失敗したら、原因を直して同じコマンドをもう一度
- 課題タイプの名前が独自なら `--type-map story=要望,epic=Initiative`
- 担当者は Jira のユーザーに自動では割り当てない（資料の表記を説明に書く）。割り当てはユーザーに任せる

## 6. 報告
作成した課題のキーと URL（出力の `browse`）、作らなかったもの（errors）と理由、`open_questions` をまとめて伝える。
Atlassian のコネクタ（MCP）しか使えない環境では、issues.json を正本にして、コネクタで1件ずつ作ってもよい。その場合は二重登録の防止がないので、作ったキーを `jira_state.json` と同じ形で記録しながら進める。
