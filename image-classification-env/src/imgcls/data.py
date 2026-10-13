from collections import Counter
from pathlib import Path

import torch
from PIL import Image
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from .common import list_images

MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


def build_transforms(img_size, train):
    if train:
        return transforms.Compose([
            transforms.RandomResizedCrop(img_size, scale=(0.7, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(0.2, 0.2, 0.2),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD),
        ])
    return transforms.Compose([
        transforms.Resize(int(img_size * 1.14)),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def scan_split(split_dir, class_names=None):
    """split_dir/<class>/*.img を (path, label) のリストにする。"""
    split_dir = Path(split_dir)
    if class_names is None:
        class_names = sorted(d.name for d in split_dir.iterdir() if d.is_dir())
    samples = []
    for idx, name in enumerate(class_names):
        cls_dir = split_dir / name
        if cls_dir.is_dir():
            samples += [(p, idx) for p in list_images(cls_dir)]
    return samples, class_names


class ImageListDataset(Dataset):
    def __init__(self, samples, transform):
        self.samples, self.transform = samples, transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        with Image.open(path) as img:
            img = img.convert("RGB")
        return self.transform(img), label


def build_datasets(cfg):
    d = cfg["data"]
    root = Path(d["data_dir"])
    train_dir = root / "train"
    if not train_dir.is_dir():
        raise FileNotFoundError(
            f"{train_dir} がありません。data/README.md の形で画像を置いてください。")
    train_samples, class_names = scan_split(train_dir)
    if len(class_names) < 2:
        raise ValueError(f"クラスが {len(class_names)} 個です。2クラス以上必要です。")

    val_dir = root / "val"
    if val_dir.is_dir():
        val_samples, _ = scan_split(val_dir, class_names)
    else:
        labels = [y for _, y in train_samples]
        train_samples, val_samples = train_test_split(
            train_samples, test_size=d["val_ratio"], stratify=labels,
            random_state=cfg["train"]["seed"])

    size = d["img_size"]
    train_ds = ImageListDataset(train_samples, build_transforms(size, True))
    val_ds = ImageListDataset(val_samples, build_transforms(size, False))
    return train_ds, val_ds, class_names


def class_counts(samples, num_classes):
    c = Counter(y for _, y in samples)
    return [c.get(i, 0) for i in range(num_classes)]


def make_loader(ds, batch_size, shuffle, num_workers, device):
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle,
                      num_workers=num_workers, pin_memory=device.type == "cuda",
                      persistent_workers=num_workers > 0)


def class_weights(samples, num_classes):
    counts = torch.tensor(class_counts(samples, num_classes), dtype=torch.float)
    w = counts.sum() / (num_classes * counts.clamp(min=1))
    return w
