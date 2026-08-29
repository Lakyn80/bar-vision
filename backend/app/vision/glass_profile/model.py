from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GlassGeometryModelConfig:
    architecture: str = "mobilenet_v3_small_multitask_geometry"
    profile_key: str = "glass_500ml_v1"
    input_width: int = 512
    input_height: int = 512
    mask_size: int = 64
    num_classes: int = 2
    num_keypoints: int = 6
    pretrained_backbone: bool = True
    dropout: float = 0.10

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LossWeights:
    classification: float = 1.0
    bbox: float = 2.0
    keypoints: float = 3.0
    mask: float = 2.0


def build_glass_geometry_model(config: GlassGeometryModelConfig):
    """
    Build the transfer-learning geometry model.

    The backbone is TorchVision MobileNetV3 Small with ImageNet weights by
    default. Heads predict profile acceptance, normalized bbox, keypoints, and
    a low-resolution mask. This is not a milliliter estimator.
    """
    import torch
    import torch.nn.functional as functional
    from torch import nn
    from torchvision.models import (
        MobileNet_V3_Small_Weights,
        mobilenet_v3_small,
    )

    if config.architecture != "mobilenet_v3_small_multitask_geometry":
        raise ValueError(f"Unsupported architecture: {config.architecture}")

    weights = (
        MobileNet_V3_Small_Weights.DEFAULT
        if config.pretrained_backbone
        else None
    )
    base = mobilenet_v3_small(weights=weights)
    feature_channels = int(base.classifier[0].in_features)

    class GlassGeometryNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.features = base.features
            self.pool = nn.AdaptiveAvgPool2d((1, 1))
            hidden = 256
            self.shared = nn.Sequential(
                nn.Flatten(),
                nn.Linear(feature_channels, hidden),
                nn.Hardswish(),
                nn.Dropout(config.dropout),
            )
            self.profile_head = nn.Linear(hidden, config.num_classes)
            self.bbox_head = nn.Sequential(
                nn.Linear(hidden, 4),
                nn.Sigmoid(),
            )
            self.keypoint_head = nn.Sequential(
                nn.Linear(hidden, config.num_keypoints * 3),
                nn.Sigmoid(),
            )
            self.mask_head = nn.Sequential(
                nn.Conv2d(feature_channels, 128, kernel_size=3, padding=1),
                nn.BatchNorm2d(128),
                nn.Hardswish(),
                nn.Conv2d(128, 1, kernel_size=1),
            )

        def forward(self, images):
            features = self.features(images)
            shared = self.shared(self.pool(features))
            raw_bbox = self.bbox_head(shared)
            left = torch.minimum(raw_bbox[:, 0], raw_bbox[:, 2])
            top = torch.minimum(raw_bbox[:, 1], raw_bbox[:, 3])
            right = torch.maximum(raw_bbox[:, 0], raw_bbox[:, 2])
            bottom = torch.maximum(raw_bbox[:, 1], raw_bbox[:, 3])
            keypoints = self.keypoint_head(shared).reshape(
                -1,
                config.num_keypoints,
                3,
            )
            mask_logits = functional.interpolate(
                self.mask_head(features),
                size=(config.mask_size, config.mask_size),
                mode="bilinear",
                align_corners=False,
            )
            return {
                "profile_logits": self.profile_head(shared),
                "bbox": torch.stack((left, top, right, bottom), dim=1),
                "keypoints": keypoints,
                "mask_logits": mask_logits,
            }

    return GlassGeometryNet()


def freeze_backbone(model, *, frozen: bool) -> None:
    if not hasattr(model, "features"):
        raise ValueError("Model does not expose a features backbone.")
    for parameter in model.features.parameters():
        parameter.requires_grad = not frozen


def compute_multitask_loss(
    outputs: dict[str, Any],
    targets: dict[str, Any],
    *,
    weights: LossWeights | None = None,
) -> tuple[Any, dict[str, float]]:
    import torch
    import torch.nn.functional as functional

    weights = weights or LossWeights()
    profile_label = targets["profile_label"]
    positive = profile_label == 1

    classification_loss = functional.cross_entropy(
        outputs["profile_logits"],
        profile_label,
    )

    zero = outputs["profile_logits"].sum() * 0.0
    bbox_loss = (
        functional.mse_loss(outputs["bbox"][positive], targets["bbox"][positive])
        if bool(torch.any(positive))
        else zero
    )

    predicted_keypoints = outputs["keypoints"]
    expected_keypoints = targets["keypoints"]
    visible = (expected_keypoints[..., 2] > 0) & positive[:, None]
    keypoint_loss = (
        functional.mse_loss(
            predicted_keypoints[..., :2][visible],
            expected_keypoints[..., :2][visible],
        )
        if bool(torch.any(visible))
        else zero
    )

    mask_loss = functional.binary_cross_entropy_with_logits(
        outputs["mask_logits"],
        targets["mask"],
    )

    total = (
        weights.classification * classification_loss
        + weights.bbox * bbox_loss
        + weights.keypoints * keypoint_loss
        + weights.mask * mask_loss
    )
    metrics = {
        "loss": float(total.detach().cpu()),
        "classification_loss": float(classification_loss.detach().cpu()),
        "bbox_loss": float(bbox_loss.detach().cpu()),
        "keypoint_loss": float(keypoint_loss.detach().cpu()),
        "mask_loss": float(mask_loss.detach().cpu()),
    }
    return total, metrics
