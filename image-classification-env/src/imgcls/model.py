import timm
import torch


def build_model(name, num_classes, pretrained=True, drop_rate=0.0):
    return timm.create_model(name, pretrained=pretrained, num_classes=num_classes,
                             drop_rate=drop_rate)


def set_backbone_trainable(model, trainable):
    head = model.get_classifier()
    head_params = {id(p) for p in head.parameters()}
    for p in model.parameters():
        if id(p) not in head_params:
            p.requires_grad = trainable


def load_checkpoint(path, device):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model = build_model(ckpt["model_name"], len(ckpt["class_names"]), pretrained=False)
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()
    return model, ckpt
