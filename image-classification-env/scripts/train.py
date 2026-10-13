"""学習: python scripts/train.py --config configs/default.yaml"""
import argparse
import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path

import _path  # noqa: F401
import torch
from torch import nn
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from imgcls.common import get_device, load_config, seed_everything
from imgcls.data import build_datasets, class_counts, class_weights, make_loader
from imgcls.model import build_model, set_backbone_trainable


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None, use_amp=False):
    train = optimizer is not None
    model.train(train)
    total_loss, correct, n = 0.0, 0, 0
    for x, y in tqdm(loader, leave=False, desc="train" if train else "val"):
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.set_grad_enabled(train), torch.autocast(device.type, enabled=use_amp):
            logits = model(x)
            loss = criterion(logits, y)
        if train:
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        total_loss += loss.item() * x.size(0)
        correct += (logits.argmax(1) == y).sum().item()
        n += x.size(0)
    return total_loss / n, correct / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    t, m = cfg["train"], cfg["model"]
    seed_everything(t["seed"])
    device = get_device()
    use_amp = bool(t["amp"]) and device.type == "cuda"

    train_ds, val_ds, class_names = build_datasets(cfg)
    nc = len(class_names)
    print(f"device={device}  classes={nc}  train={len(train_ds)}  val={len(val_ds)}")
    for name, a, b in zip(class_names, class_counts(train_ds.samples, nc),
                          class_counts(val_ds.samples, nc)):
        print(f"  {name}: train {a} / val {b}")

    nw, bs = cfg["data"]["num_workers"], t["batch_size"]
    train_dl = make_loader(train_ds, bs, True, nw, device)
    val_dl = make_loader(val_ds, bs, False, nw, device)

    model = build_model(m["name"], nc, m["pretrained"], m.get("drop_rate", 0.0)).to(device)
    weight = class_weights(train_ds.samples, nc).to(device) if t["class_weighting"] else None
    criterion = nn.CrossEntropyLoss(weight=weight, label_smoothing=t["label_smoothing"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=t["lr"], weight_decay=t["weight_decay"])
    total, warm = t["epochs"], t["warmup_epochs"]
    sched = torch.optim.lr_scheduler.LambdaLR(optimizer, lambda e: (e + 1) / (warm + 1) if e < warm
                                              else 0.5 * (1 + math.cos(math.pi * (e - warm) / max(1, total - warm))))
    scaler = torch.amp.GradScaler(device.type, enabled=use_amp)

    run = cfg["output"]["run_name"] or datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(cfg["output"]["dir"]) / run
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "class_names.json").write_text(json.dumps(class_names, ensure_ascii=False), encoding="utf-8")
    writer = SummaryWriter(out / "tb")

    best_acc, bad = -1.0, 0
    hist = open(out / "history.csv", "w", newline="", encoding="utf-8")
    w = csv.writer(hist)
    w.writerow(["epoch", "lr", "train_loss", "train_acc", "val_loss", "val_acc", "sec"])
    for epoch in range(1, total + 1):
        set_backbone_trainable(model, epoch > t["freeze_backbone_epochs"])
        t0 = time.time()
        lr = optimizer.param_groups[0]["lr"]
        tr_loss, tr_acc = run_epoch(model, train_dl, criterion, device, optimizer, scaler, use_amp)
        va_loss, va_acc = run_epoch(model, val_dl, criterion, device, use_amp=use_amp)
        sched.step()
        sec = time.time() - t0
        w.writerow([epoch, f"{lr:.2e}", f"{tr_loss:.4f}", f"{tr_acc:.4f}", f"{va_loss:.4f}", f"{va_acc:.4f}", f"{sec:.1f}"])
        hist.flush()
        for k, v in {"loss/train": tr_loss, "loss/val": va_loss, "acc/train": tr_acc, "acc/val": va_acc}.items():
            writer.add_scalar(k, v, epoch)
        mark = ""
        if va_acc > best_acc:
            best_acc, bad, mark = va_acc, 0, "  * best"
            torch.save({"state_dict": model.state_dict(), "model_name": m["name"],
                        "class_names": class_names, "img_size": cfg["data"]["img_size"],
                        "epoch": epoch, "val_acc": va_acc}, out / "best.pt")
        else:
            bad += 1
        print(f"[{epoch:3d}/{total}] train loss {tr_loss:.4f} acc {tr_acc:.3f} | "
              f"val loss {va_loss:.4f} acc {va_acc:.3f} | {sec:.0f}s{mark}")
        if bad >= t["early_stopping_patience"]:
            print(f"early stopping（{bad} エポック改善なし）")
            break
    hist.close()
    writer.close()
    print(f"\n完了: best val acc = {best_acc:.4f}\nモデル: {out / 'best.pt'}")


if __name__ == "__main__":
    main()
