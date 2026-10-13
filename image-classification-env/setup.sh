#!/usr/bin/env bash
# 画像分類の学習環境セットアップ（Linux / macOS / WSL）
#   bash setup.sh            GPU を自動判定
#   TORCH_VARIANT=cpu bash setup.sh     強制的に CPU 版
#   TORCH_VARIANT=cu128 bash setup.sh   CUDA 版を指定（cu126 / cu128 / cu130）
set -euo pipefail
cd "$(dirname "$0")"
PY_VERSION="${PY_VERSION:-3.12}"

# 1) uv（高速な Python パッケージ管理）を用意
if ! command -v uv >/dev/null 2>&1; then
  echo "[1/4] uv をインストールします"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "[1/4] uv $(uv --version | awk '{print $2}')"

# 2) 仮想環境（Python は uv が自動で取得する）
echo "[2/4] .venv を作成（Python ${PY_VERSION}）"
uv venv --python "${PY_VERSION}" --allow-existing .venv

# 3) PyTorch（GPU に合わせて選ぶ）
variant="${TORCH_VARIANT:-auto}"
if [ "$variant" = "auto" ]; then
  variant=cpu
  if [ "$(uname -s)" = "Linux" ] && command -v nvidia-smi >/dev/null 2>&1; then
    cuda=$(nvidia-smi 2>/dev/null | grep -oE 'CUDA Version: [0-9]+\.[0-9]+' | awk '{print $3}' || true)
    if [ -n "$cuda" ]; then
      major=${cuda%.*}; minor=${cuda#*.}; v=$((major * 100 + minor))
      if   [ $v -ge 1300 ]; then variant=cu130
      elif [ $v -ge 1208 ]; then variant=cu128
      elif [ $v -ge 1206 ]; then variant=cu126
      else echo "⚠ GPU ドライバが古い（CUDA ${cuda}）ため CPU 版を入れます。ドライバ更新後に再実行してください。"
      fi
    fi
  fi
fi
echo "[3/4] PyTorch をインストール（${variant}）"
if [ "$(uname -s)" = "Darwin" ]; then
  uv pip install --python .venv torch torchvision           # macOS は通常版で MPS が使える
else
  uv pip install --python .venv torch torchvision --index-url "https://download.pytorch.org/whl/${variant}"
fi

# 4) その他のライブラリ
echo "[4/4] ライブラリをインストール"
uv pip install --python .venv -r requirements.txt

echo
echo "セットアップ完了。動作確認:"
echo "  source .venv/bin/activate && python scripts/verify_env.py"
