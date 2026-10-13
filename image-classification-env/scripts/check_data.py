"""データ確認: python scripts/check_data.py [--data_dir data/dataset]
クラスごとの枚数、壊れて開けない画像、極端な偏りを報告する。"""
import argparse
from pathlib import Path

import _path  # noqa: F401
from PIL import Image

from imgcls.common import list_images


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="data/dataset")
    args = ap.parse_args()
    root = Path(args.data_dir)
    if not (root / "train").is_dir():
        raise SystemExit(f"{root / 'train'} がありません。data/README.md を参照してください。")
    broken = []
    for split in ("train", "val", "test"):
        d = root / split
        if not d.is_dir():
            continue
        print(f"[{split}]")
        counts = {}
        for cls in sorted(x for x in d.iterdir() if x.is_dir()):
            imgs = list_images(cls)
            counts[cls.name] = len(imgs)
            for p in imgs:
                try:
                    with Image.open(p) as im:
                        im.verify()
                except Exception as e:  # noqa: BLE001
                    broken.append((p, e))
            print(f"  {cls.name:30s} {len(imgs):6d}")
        if counts:
            lo, hi = min(counts.values()), max(counts.values())
            if lo == 0:
                print("  ⚠ 0枚のクラスがあります")
            elif hi / lo >= 5:
                print(f"  ⚠ 枚数の偏りが大きい（最大/最小 = {hi / lo:.1f}）。class_weighting: true を検討")
    if broken:
        print(f"\n⚠ 開けない画像 {len(broken)} 件（削除するか差し替えてください）:")
        for p, e in broken[:50]:
            print(f"  {p}: {e}")
    else:
        print("\n壊れた画像はありません")


if __name__ == "__main__":
    main()
