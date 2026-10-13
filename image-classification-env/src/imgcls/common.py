import random
from pathlib import Path

import numpy as np
import torch
import yaml

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def list_images(folder):
    folder = Path(folder)
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMG_EXTS)
