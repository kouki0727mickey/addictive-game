# データの置き方

```
data/dataset/
├── train/
│   ├── cat/   001.jpg, 002.jpg, ...
│   ├── dog/
│   └── bird/
├── val/       （任意。なければ train から自動で分ける）
└── test/      （任意。最終評価用。学習には使わない）
```

- フォルダ名がそのままクラス名になる
- 対応形式: jpg / jpeg / png / bmp / webp / tif
- 目安: 1クラス 100 枚以上。少ない場合は `freeze_backbone_epochs: 3` などを試す
- `python scripts/check_data.py` で枚数と壊れた画像を確認できる
