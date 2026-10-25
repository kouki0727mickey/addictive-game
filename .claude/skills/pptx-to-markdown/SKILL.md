---
name: pptx-to-markdown
description: PowerPoint（.pptx）を、テキスト・表・グラフ・SmartArt・画像・発表者ノートを落とさずに Markdown にする（抽出 → vLLM の視覚言語モデルで整形 → 網羅率の検査）。「パワポをMarkdownにしたい」「スライドの中身をテキストで取り出したい」と言われたとき、または Jira 以外の用途（要約・検索・RAG）に使う。Jira に登録するなら /pptx-to-jira を使う。
---

# PowerPoint を Markdown にする

`/pptx-to-jira` の手順 0〜2 と同じ。道具は `tools/pptx2jira/`（なければ `git clone --depth 1 https://github.com/kouki0727mickey/addictive-game /tmp/ai-ent-kb`）。
`T=tools/pptx2jira`、`W=p2j-work/<資料名>`。

```bash
python3 $T/extract.py <資料.pptx> -o $W            # 抽出。$W/extracted.md は VLM なしの Markdown
python3 $T/vlm_markdown.py $W --dry-run            # 呼び出しの見積もり
python3 $T/vlm_markdown.py $W                      # VLLM_BASE_URL / VLLM_MODEL を使う
```

できあがりは `$W/deck.md`（スライドごとに `<!-- slide: N -->` の区切りつき）。

確かめること:
- 出力の `status` に `fallback` / `error_fallback` があるスライド、`invented_numbers` があるスライドは、`$W/renders/slide-NNN.png` を Read で開いて見比べる
- `$W/vlm_report.json` の `coverage`（原文の網羅率。既定の合格は 0.95）と `missing`（落ちた行）
- 表とグラフの値は VLM に書かせず、抽出した値で差し込んでいる。表が崩れていたら抽出（`slides.json` の table）を確かめる

vLLM がなければ `extracted.md` をそのまま使い、図が重要なスライドだけ render の PNG を Read で見て `> 図: ` の説明を足す。
