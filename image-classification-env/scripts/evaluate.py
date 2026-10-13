"""評価: python scripts/evaluate.py --ckpt outputs/<run>/best.pt [--split test]
混同行列・クラス別の適合率/再現率・誤分類一覧を checkpoint と同じフォルダに保存する。"""
import argparse
import csv
import json
from pathlib import Path

import _path  # noqa: F401
import matplotlib
import torch
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix

from imgcls.common import get_device
from imgcls.data import ImageListDataset, build_transforms, scan_split
from imgcls.model import load_checkpoint

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--data_dir", default=None, help="省略時は学習時の data_dir")
    ap.add_argument("--split", default="test", help="test / val など（フォルダ名）")
    ap.add_argument("--batch_size", type=int, default=64)
    args = ap.parse_args()

    device = get_device()
    model, ckpt = load_checkpoint(args.ckpt, device)
    out = Path(args.ckpt).parent
    cfg = json.loads((out / "config.json").read_text(encoding="utf-8"))
    root = Path(args.data_dir or cfg["data"]["data_dir"])
    split_dir = root / args.split
    if not split_dir.is_dir():
        raise SystemExit(f"{split_dir} がありません。--split val などを指定してください。")
    names = ckpt["class_names"]
    samples, _ = scan_split(split_dir, names)
    ds = ImageListDataset(samples, build_transforms(ckpt["img_size"], False))
    dl = torch.utils.data.DataLoader(ds, batch_size=args.batch_size)

    preds, probs = [], []
    with torch.no_grad():
        for x, _ in dl:
            p = model(x.to(device)).softmax(1).cpu()
            probs.append(p)
            preds.append(p.argmax(1))
    preds = torch.cat(preds).tolist()
    probs = torch.cat(probs)
    labels = [y for _, y in samples]

    report = classification_report(labels, preds, labels=range(len(names)), target_names=names,
                                   digits=4, zero_division=0)
    print(report)
    (out / f"report_{args.split}.txt").write_text(report, encoding="utf-8")

    cm = confusion_matrix(labels, preds, labels=range(len(names)))
    fig, ax = plt.subplots(figsize=(max(6, len(names) * 0.6), max(5, len(names) * 0.5)))
    ConfusionMatrixDisplay(cm, display_labels=names).plot(ax=ax, xticks_rotation=45, colorbar=False)
    fig.tight_layout()
    fig.savefig(out / f"confusion_{args.split}.png", dpi=150)

    with open(out / f"errors_{args.split}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "true", "pred", "confidence"])
        for (path, y), p, pr in zip(samples, preds, probs):
            if y != p:
                w.writerow([path, names[y], names[p], f"{pr[p]:.4f}"])
    print(f"保存先: {out}")


if __name__ == "__main__":
    main()
