"""推論: python scripts/predict.py --ckpt outputs/<run>/best.pt --input 画像 or フォルダ [--topk 3] [--csv out.csv]"""
import argparse
import csv
from pathlib import Path

import _path  # noqa: F401
import torch
from PIL import Image

from imgcls.common import IMG_EXTS, get_device, list_images
from imgcls.data import build_transforms
from imgcls.model import load_checkpoint


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    device = get_device()
    model, ckpt = load_checkpoint(args.ckpt, device)
    names = ckpt["class_names"]
    tf = build_transforms(ckpt["img_size"], False)
    src = Path(args.input)
    paths = [src] if src.suffix.lower() in IMG_EXTS else list_images(src)
    k = min(args.topk, len(names))

    rows = []
    with torch.no_grad():
        for p in paths:
            with Image.open(p) as img:
                x = tf(img.convert("RGB")).unsqueeze(0).to(device)
            prob = model(x).softmax(1)[0].cpu()
            top = prob.topk(k)
            preds = [(names[i], float(v)) for v, i in zip(top.values, top.indices)]
            rows.append([str(p)] + [f"{n}:{v:.4f}" for n, v in preds])
            print(p, " ".join(f"{n}={v:.3f}" for n, v in preds))
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["path"] + [f"top{i + 1}" for i in range(k)])
            w.writerows(rows)


if __name__ == "__main__":
    main()
