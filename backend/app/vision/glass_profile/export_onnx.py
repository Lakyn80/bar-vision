from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.vision.glass_profile.model import (
    GlassGeometryModelConfig,
    build_glass_geometry_model,
)
from app.vision.glass_profile.schema import KEYPOINT_NAMES


class OnnxExportError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def export_checkpoint_to_onnx(
    *,
    checkpoint_path: Path,
    output_path: Path,
    metadata_path: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    import torch

    if not checkpoint_path.is_file():
        raise OnnxExportError("Checkpoint does not exist.")
    if output_path.exists() and not overwrite:
        raise OnnxExportError("ONNX output already exists; pass overwrite explicitly.")
    if metadata_path.exists() and not overwrite:
        raise OnnxExportError("Metadata output already exists; pass overwrite explicitly.")

    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=False,
    )
    model_config = GlassGeometryModelConfig(
        **checkpoint.get("model_config", {})
    )
    model = build_glass_geometry_model(model_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dummy = torch.zeros(
        1,
        3,
        model_config.input_height,
        model_config.input_width,
        dtype=torch.float32,
    )
    torch.onnx.export(
        model,
        dummy,
        output_path,
        input_names=["image"],
        output_names=["profile_logits", "bbox", "keypoints", "mask_logits"],
        dynamic_axes={"image": {0: "batch"}},
        opset_version=18,
    )

    metadata = {
        "model_version": checkpoint.get("model_version"),
        "profile_key": model_config.profile_key,
        "architecture": model_config.architecture,
        "input_width": model_config.input_width,
        "input_height": model_config.input_height,
        "mask_size": model_config.mask_size,
        "class_mapping": {"0": "invalid", "1": model_config.profile_key},
        "keypoint_names": list(KEYPOINT_NAMES),
        "training_config": checkpoint.get("training_config"),
        "dataset_audit": checkpoint.get("dataset_audit"),
        "split": checkpoint.get("split"),
        "accepted_for_production": False,
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def _main() -> None:
    parser = argparse.ArgumentParser(description="Export glass profile checkpoint to ONNX.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    metadata = export_checkpoint_to_onnx(
        checkpoint_path=Path(args.checkpoint),
        output_path=Path(args.output),
        metadata_path=Path(args.metadata),
        overwrite=args.overwrite,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    _main()
