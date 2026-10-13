"""ONNX 書き出し: python scripts/export_onnx.py --ckpt outputs/<run>/best.pt"""
import argparse
import warnings
from pathlib import Path

import _path  # noqa: F401
import torch

from imgcls.model import load_checkpoint


def main():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    model, ckpt = load_checkpoint(args.ckpt, torch.device("cpu"))
    out = Path(args.out or Path(args.ckpt).with_suffix(".onnx"))
    s = ckpt["img_size"]
    torch.onnx.export(model, torch.randn(1, 3, s, s), out, input_names=["image"],
                      output_names=["logits"], dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
                      opset_version=17, dynamo=False)
    print(f"書き出し: {out}（入力 1x3x{s}x{s}, ImageNet 平均/分散で正規化した RGB）")


if __name__ == "__main__":
    main()
