# 環境構築プロンプト（クライアント配布用）

AI コーディングエージェント（Claude Code、Cursor、GitHub Copilot Agent など、
ターミナルでコマンドを実行できるもの）に貼り付けると、学習環境の構築から動作確認までを一度で行います。

- **プロンプト A**: このフォルダ（`image-classification-env`）を受け取っている場合。通常はこちら
- **プロンプト B**: フォルダがなく、ゼロから同じ環境を作らせたい場合

`{{ }}` の部分だけ書き換えてください（不要なら行ごと消してかまいません）。

---

## プロンプト A（フォルダを受け取っている場合）

```text
あなたは機械学習の環境構築を担当するエンジニアです。
このフォルダは画像分類モデル（PyTorch + timm）の学習環境です。以下を順に実行し、動作確認まで完了させてください。

# 前提
- 作業フォルダ: {{image-classification-env を置いた場所。例: C:\work\image-classification-env}}
- 学習用の画像: {{画像フォルダの場所。まだなければ「なし」}}

# 手順
1. README.md と SETUP_PROMPT.md を読み、構成を把握する。
2. OS と GPU を確認する（Windows / macOS / Linux / WSL、`nvidia-smi` の有無と CUDA Version）。結果を報告する。
3. セットアップを実行する。
   - Linux / macOS / WSL: `bash setup.sh`
   - Windows: `powershell -ExecutionPolicy Bypass -File setup.ps1`
4. 動作確認を実行する: 仮想環境の python で `python scripts/verify_env.py`
   - 最後に「✅ 環境構築は完了です」と出れば成功。
   - GPU があるのに「GPU なし」と出た場合は、README の「よくあるトラブル」に従って直す。
5. 学習用の画像が指定されている場合:
   - `data/dataset/train/<クラス名>/` の形になっているか確認する。なっていなければ、元の画像は消さずに、
     コピーまたはシンボリックリンクでその形に並べる（並べ方の方針は実行前に私に確認する）。
   - `python scripts/check_data.py` を実行し、クラスごとの枚数・壊れた画像・偏りを報告する。
   - 学習はまだ始めない（私が確認してから始める）。

# ルール
- スクリプトやライブラリの中身は、エラーを直すため以外に変更しない。変更したら、何をなぜ変えたかを報告する。
- 管理者権限（sudo / 管理者として実行）が必要になったら、実行前に私に確認する。
- エラーが出たら、エラー全文・原因の推定・行った対処を報告する。3回直して解決しなければ止めて相談する。
- 認証情報（APIキー、パスワード、トークン）は表示・保存しない。

# 最後に報告すること
- OS / Python / PyTorch / timm のバージョン、使用デバイス（GPU名 or CPU）
- verify_env.py の結果（成功/失敗）
- （画像がある場合）クラス数、クラスごとの枚数、気になった点
- 次に私が実行するコマンド（学習・評価・推論）
```

---

## プロンプト B（ゼロから作らせる場合）

```text
あなたは機械学習の環境構築を担当するエンジニアです。
画像分類モデルを転移学習で作るための学習環境を、次の仕様で新しく作り、動作確認まで完了させてください。

# 前提
- 作業フォルダ: {{例: ~/work/image-classification-env}}
- 対象の OS / GPU: {{例: Windows 11 + RTX 4070 / わからなければ「自動で判定」}}

# 仕様
- Python 3.12、パッケージ管理は uv、仮想環境は作業フォルダ内の .venv
- PyTorch + torchvision は GPU に合わせて選ぶ（`nvidia-smi` の CUDA Version から
  https://download.pytorch.org/whl/ の cu130 / cu128 / cu126 を選ぶ。NVIDIA GPU がなければ cpu。macOS は通常版で MPS を使う）
- その他: timm, pyyaml, numpy, pillow, scikit-learn, matplotlib, tqdm, tensorboard, onnx
- データ形式: data/dataset/train/<クラス名>/*.jpg（val がなければ train からクラス比を保って 20% を自動分割。test は任意）
- 設定は configs/default.yaml（モデル名・事前学習の有無・画像サイズ・エポック数・バッチサイズ・学習率・
  ラベルスムージング・ウォームアップ・最初の N エポックは分類層のみ学習・クラス重み・混合精度・early stopping・seed）
  既定値: efficientnet_b0（ImageNet 事前学習）、224px、20 エポック、バッチ 32、AdamW lr 3e-4、cosine 減衰
- スクリプト（scripts/ 以下、実行は作業フォルダ直下から）
  - train.py: 学習。outputs/<run名>/ に best.pt（重み・モデル名・クラス名・画像サイズを含む）、
    history.csv、TensorBoard ログ、使った設定を保存。GPU / MPS / CPU を自動選択
  - evaluate.py: 混同行列の画像、クラス別の適合率・再現率・F1、誤分類した画像の一覧（CSV）を保存
  - predict.py: 画像1枚またはフォルダを推論し、上位 k クラスと確率を表示・CSV 保存
  - export_onnx.py: ONNX に書き出す（バッチ次元は可変）
  - check_data.py: クラスごとの枚数、開けない画像、枚数の偏りを報告
  - verify_env.py: バージョンと GPU を表示し、合成画像（丸・四角・三角の3クラス）を作って
    学習→評価→推論→ONNX書き出しを CPU でも1分程度で一通り流す
- セットアップを再現するスクリプト: setup.sh（Linux/macOS/WSL）と setup.ps1（Windows）
- README.md（日本語）: セットアップ、動作確認、自分のデータでの学習手順、設定の変え方、よくあるトラブル
- .gitignore で data/ の画像と outputs/ と .venv/ を除外

# 手順
1. OS と GPU を確認して報告する。
2. 上の仕様でファイルを作り、setup スクリプトで環境を作る。
3. `python scripts/verify_env.py` を実行し、学習→評価→推論→ONNX書き出しがすべて成功するまで直す。

# ルール
- 管理者権限が必要になったら、実行前に私に確認する。
- エラーが出たら、原因と対処を報告する。3回直して解決しなければ止めて相談する。
- 認証情報は表示・保存しない。

# 最後に報告すること
- 作ったファイルの一覧と役割
- OS / Python / PyTorch / timm のバージョン、使用デバイス
- verify_env.py の結果
- 自分のデータで学習するときに実行するコマンド
```

---

## 渡すときのメモ（制作側向け）

- 通常はフォルダを zip で渡し、プロンプト A を添える。B は再現性が A より低い（エージェントによって実装が変わる）
- プロンプトには「学習はまだ始めない」「並べ替えの前に確認する」を入れてある。
  クライアントの元データを勝手に動かしたり、長時間の学習を勝手に始めたりしないため
- 社内プロキシ環境では、事前学習済み重み（Hugging Face）と PyTorch のダウンロードが止まりやすい。
  事前に `https://download.pytorch.org` と `https://huggingface.co` への通信が許可されているか確認してもらう
