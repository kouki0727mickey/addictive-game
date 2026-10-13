# 画像分類モデル 学習環境

フォルダ分けした画像から、画像分類モデルを転移学習で作るための環境です。
PyTorch + timm を使い、GPU（NVIDIA / Apple Silicon）がなくても CPU で動きます。

## 1. セットアップ（初回のみ）

| OS | コマンド |
|---|---|
| Linux / macOS / WSL | `bash setup.sh` |
| Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -File setup.ps1` |
| Docker (GPU サーバー) | `docker build -t imgcls .`（使い方は `Dockerfile` 冒頭） |

- uv（Python 管理ツール）と Python 3.12 は自動で入ります。管理者権限は不要です
- NVIDIA GPU は `nvidia-smi` のドライバ版から CUDA 版の PyTorch を自動で選びます
  - 強制したいとき: `TORCH_VARIANT=cpu`（または `cu126` / `cu128` / `cu130`）を付けて実行

## 2. 動作確認

```bash
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python scripts/verify_env.py
```

合成画像（丸・四角・三角）で「学習 → 評価 → 推論 → ONNX 書き出し」を一通り流し、
最後に `✅ 環境構築は完了です` と出れば成功です（CPU で 1 分程度）。

## 3. 自分のデータで学習

1. 画像を `data/dataset/train/<クラス名>/` に置く（詳細は `data/README.md`）
2. データ確認: `python scripts/check_data.py`
3. 学習: `python scripts/train.py --config configs/default.yaml`
4. 評価: `python scripts/evaluate.py --ckpt outputs/<run名>/best.pt --split test`
   （test がなければ `--split val`）→ 混同行列・クラス別スコア・誤分類一覧を保存
5. 推論: `python scripts/predict.py --ckpt outputs/<run名>/best.pt --input 画像かフォルダ --csv result.csv`
6. 配布用: `python scripts/export_onnx.py --ckpt outputs/<run名>/best.pt`

学習曲線は `tensorboard --logdir outputs` で見られます（`history.csv` にも保存）。

## 4. 設定の変え方（`configs/default.yaml`）

| やりたいこと | 設定 |
|---|---|
| 精度を上げたい | `model.name` を `convnext_tiny` などに、`img_size` を 288〜384 に |
| 速く・軽くしたい | `model.name: mobilenetv3_large_100` |
| データが少ない（1クラス数十枚） | `freeze_backbone_epochs: 3`、`epochs` を増やす |
| クラスの枚数が偏っている | `class_weighting: true` |
| `CUDA out of memory` | `batch_size` を 16 → 8 と下げる |
| Windows で学習が始まらない | `num_workers: 0` |

設定ファイルはコピーして `--config configs/xxx.yaml` で切り替えられます。

## 構成

```
setup.sh / setup.ps1 / Dockerfile   環境構築
requirements.txt                    PyTorch 以外のライブラリ
configs/default.yaml                学習設定
configs/smoke_test.yaml             動作確認用設定
src/imgcls/                         データ・モデルの共通処理
scripts/                            train / evaluate / predict / export_onnx / check_data / verify_env
data/                               画像を置く場所（git 管理外）
outputs/                            学習結果（git 管理外）
SETUP_PROMPT.md                     AI エージェントに環境構築を任せるためのプロンプト
```

## よくあるトラブル

- **GPU があるのに `device=cpu`**: `nvidia-smi` が動くか確認 → ドライバ更新 → `TORCH_VARIANT=cu126 bash setup.sh` で入れ直す
- **事前学習済み重みがダウンロードできない（社内プロキシ等）**: `HTTPS_PROXY` を設定するか、`pretrained: false` で動作確認だけ行う
- **`PowerShell のスクリプト実行が無効`**: コマンドに `-ExecutionPolicy Bypass` を付けているか確認
