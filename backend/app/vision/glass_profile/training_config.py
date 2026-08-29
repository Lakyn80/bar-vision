from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AugmentationConfig:
    brightness: float = 0.12
    contrast: float = 0.12
    blur_probability: float = 0.10
    noise_std: float = 0.015


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    model_version: str
    profile_key: str
    dataset_annotation: str
    output_dir: str
    architecture: str = "mobilenet_v3_small_multitask_geometry"
    input_width: int = 512
    input_height: int = 512
    mask_size: int = 64
    batch_size: int = 2
    gradient_accumulation_steps: int = 1
    learning_rate: float = 1e-4
    optimizer: str = "adamw"
    weight_decay: float = 1e-4
    epochs: int = 20
    scheduler: str = "cosine"
    random_seed: int = 20260829
    pretrained_checkpoint: str = "torchvision.mobilenet_v3_small.IMAGENET1K_V1"
    pretrained_backbone: bool = True
    freeze_backbone_epochs: int = 1
    amp: bool = True
    require_cuda: bool = True
    train_split_version: str = "glass_500ml_v1-v1-seed-20260829"
    allow_bbox_mask_fallback: bool = False
    augmentation: AugmentationConfig = field(default_factory=AugmentationConfig)

    @classmethod
    def from_json_file(cls, path: Path) -> "TrainingConfig":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Training config must be a JSON object.")
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrainingConfig":
        data = dict(payload)
        augmentation_payload = data.pop("augmentation", None)
        augmentation = (
            AugmentationConfig(**augmentation_payload)
            if isinstance(augmentation_payload, dict)
            else AugmentationConfig()
        )
        return cls(**data, augmentation=augmentation)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
