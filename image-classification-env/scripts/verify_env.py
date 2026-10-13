"""環境確認: python scripts/verify_env.py [--skip-train]
ライブラリ・GPU を確認し、合成画像で 学習→評価→推論→ONNX書き出し を一通り流す。"""
import argparse
import platform
import subprocess
import sys
from pathlib import Path

import _path  # noqa: F401
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def make_smoke_data(root, n_per_class=24, size=64):
    """丸・四角・三角の3クラスの合成画像を作る。"""
    rng = np.random.default_rng(0)
    for split, n in (("train", n_per_class), ("test", 8)):
        for cls in ("circle", "square", "triangle"):
            d = root / split / cls
            d.mkdir(parents=True, exist_ok=True)
            for i in range(n):
                bg = tuple(int(v) for v in rng.integers(0, 120, 3))
                fg = tuple(int(v) for v in rng.integers(150, 256, 3))
                img = Image.new("RGB", (size, size), bg)
                dr = ImageDraw.Draw(img)
                r = int(rng.integers(14, 26))
                cx, cy = (int(v) for v in rng.integers(r, size - r, 2))
                if cls == "circle":
                    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)
                elif cls == "square":
                    dr.rectangle([cx - r, cy - r, cx + r, cy + r], fill=fg)
                else:
                    dr.polygon([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)], fill=fg)
                img.save(d / f"{i:03d}.png")


def step(title, cmd):
    print(f"\n=== {title} ===")
    r = subprocess.run([sys.executable, *cmd], cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"✗ {title} で失敗しました（終了コード {r.returncode}）")
    print(f"✓ {title}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-train", action="store_true")
    args = ap.parse_args()

    import timm
    import torch
    import torchvision
    print(f"Python      {platform.python_version()} ({platform.system()})")
    print(f"torch       {torch.__version__}")
    print(f"torchvision {torchvision.__version__}")
    print(f"timm        {timm.__version__}")
    if torch.cuda.is_available():
        print(f"GPU         {torch.cuda.get_device_name(0)} (CUDA {torch.version.cuda})")
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        print("GPU         Apple Silicon (MPS)")
    else:
        print("GPU         なし（CPU で動作。学習は遅くなります）")
    if args.skip_train:
        return

    smoke = ROOT / "data" / "smoke"
    if not smoke.exists():
        make_smoke_data(smoke)
    ckpt = "outputs/smoke_test/best.pt"
    step("学習", ["scripts/train.py", "--config", "configs/smoke_test.yaml"])
    step("評価", ["scripts/evaluate.py", "--ckpt", ckpt, "--split", "test"])
    step("推論", ["scripts/predict.py", "--ckpt", ckpt, "--input", "data/smoke/test/circle/000.png"])
    step("ONNX書き出し", ["scripts/export_onnx.py", "--ckpt", ckpt])
    print("\n✅ 環境構築は完了です。data/dataset/ に画像を置いて scripts/train.py を実行してください。")


if __name__ == "__main__":
    main()
