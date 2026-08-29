from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.vision.glass_profile.dataset import (
    GlassProfileTorchDataset,
    audit_glass_profile_dataset,
    collate_glass_profile_batch,
    create_deterministic_split,
    samples_for_images,
)
from app.vision.glass_profile.model import (
    GlassGeometryModelConfig,
    build_glass_geometry_model,
    compute_multitask_loss,
    freeze_backbone,
)
from app.vision.glass_profile.schema import load_glass_profile_annotations
from app.vision.glass_profile.training_config import TrainingConfig


class TrainingRuntimeError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CudaRuntimeReport:
    torch_version: str
    cuda_available: bool
    cuda_runtime_version: str | None
    gpu_name: str | None
    total_vram_mb: int | None
    free_vram_mb: int | None
    tensor_smoke_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_cuda_runtime(*, require_cuda: bool) -> CudaRuntimeReport:
    import torch

    cuda_available = bool(torch.cuda.is_available())
    tensor_smoke_ok = False
    gpu_name: str | None = None
    free_vram_mb: int | None = None
    total_vram_mb: int | None = None
    if cuda_available:
        gpu_name = torch.cuda.get_device_name(0)
        free_bytes, total_bytes = torch.cuda.mem_get_info(0)
        free_vram_mb = int(free_bytes // (1024 * 1024))
        total_vram_mb = int(total_bytes // (1024 * 1024))
        probe = torch.ones((32, 32), device="cuda")
        tensor_smoke_ok = bool(float((probe @ probe).sum().detach().cpu()) > 0)

    report = CudaRuntimeReport(
        torch_version=str(torch.__version__),
        cuda_available=cuda_available,
        cuda_runtime_version=str(torch.version.cuda)
        if torch.version.cuda
        else None,
        gpu_name=gpu_name,
        total_vram_mb=total_vram_mb,
        free_vram_mb=free_vram_mb,
        tensor_smoke_ok=tensor_smoke_ok,
    )
    if require_cuda and not (report.cuda_available and report.tensor_smoke_ok):
        raise TrainingRuntimeError("CUDA PyTorch runtime is not available.")
    return report


def run_training(
    *,
    datasets_root: Path,
    config: TrainingConfig,
    audit_only: bool = False,
    allow_cpu: bool = False,
) -> dict[str, Any]:
    document = load_glass_profile_annotations(
        datasets_root=datasets_root,
        annotation_relative_path=config.dataset_annotation,
    )
    audit = audit_glass_profile_dataset(document, inspect_images=True)
    split = create_deterministic_split(
        document.samples,
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        seed=config.random_seed,
        split_version=config.train_split_version,
    )

    report: dict[str, Any] = {
        "model_version": config.model_version,
        "dataset_id": document.dataset_id,
        "dataset_version": document.dataset_version,
        "created_at": datetime.now(UTC).isoformat(),
        "audit": audit.to_dict(),
        "split": split.to_dict(),
        "training_config": config.to_dict(),
        "status": "audit_only" if audit_only else "not_started",
    }
    if audit_only:
        return report
    if not audit.ready_for_fine_tuning:
        report["status"] = "blocked_insufficient_annotations"
        return report

    import torch
    from torch.utils.data import DataLoader

    torch.manual_seed(config.random_seed)
    import numpy as np

    np.random.seed(config.random_seed)

    cuda_report = inspect_cuda_runtime(
        require_cuda=config.require_cuda and not allow_cpu
    )
    report["cuda"] = cuda_report.to_dict()
    device = torch.device("cuda" if cuda_report.cuda_available else "cpu")

    model_config = GlassGeometryModelConfig(
        architecture=config.architecture,
        profile_key=config.profile_key,
        input_width=config.input_width,
        input_height=config.input_height,
        mask_size=config.mask_size,
        pretrained_backbone=config.pretrained_backbone,
    )
    model = build_glass_geometry_model(model_config).to(device)
    freeze_backbone(model, frozen=config.freeze_backbone_epochs > 0)

    train_samples = samples_for_images(document.samples, split.train)
    validation_samples = samples_for_images(document.samples, split.validation)
    train_dataset = GlassProfileTorchDataset(
        train_samples,
        input_size=(config.input_width, config.input_height),
        mask_size=config.mask_size,
        allow_bbox_mask_fallback=config.allow_bbox_mask_fallback,
        augmentation=asdict(config.augmentation),
    )
    validation_dataset = GlassProfileTorchDataset(
        validation_samples,
        input_size=(config.input_width, config.input_height),
        mask_size=config.mask_size,
        allow_bbox_mask_fallback=config.allow_bbox_mask_fallback,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        collate_fn=collate_glass_profile_batch,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        collate_fn=collate_glass_profile_batch,
    )

    if config.optimizer != "adamw":
        raise TrainingRuntimeError(f"Unsupported optimizer: {config.optimizer}")
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = _build_scheduler(torch, optimizer, config.scheduler, config.epochs)
    scaler = torch.amp.GradScaler("cuda", enabled=config.amp and device.type == "cuda")

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    best_loss = float("inf")
    history: list[dict[str, float]] = []

    for epoch in range(config.epochs):
        if epoch == config.freeze_backbone_epochs:
            freeze_backbone(model, frozen=False)
            optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=config.learning_rate,
                weight_decay=config.weight_decay,
            )
            scheduler = _build_scheduler(torch, optimizer, config.scheduler, config.epochs)

        train_loss = _run_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            scaler=scaler,
            device=device,
            amp=config.amp,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
        )
        validation_loss = _validate_epoch(
            model=model,
            loader=validation_loader,
            device=device,
            amp=config.amp,
        )
        if scheduler is not None:
            scheduler.step()
        history.append(
            {
                "epoch": float(epoch + 1),
                "train_loss": train_loss,
                "validation_loss": validation_loss,
            }
        )

        checkpoint = {
            "model_version": config.model_version,
            "model_config": model_config.to_dict(),
            "training_config": config.to_dict(),
            "dataset_audit": audit.to_dict(),
            "split": split.to_dict(),
            "history": history,
            "model_state_dict": model.state_dict(),
        }
        torch.save(checkpoint, output_dir / "last.pt")
        if validation_loss < best_loss:
            best_loss = validation_loss
            torch.save(checkpoint, output_dir / "best.pt")

    report["status"] = "trained"
    report["history"] = history
    report["checkpoint_last"] = str(output_dir / "last.pt")
    report["checkpoint_best"] = str(output_dir / "best.pt")
    (output_dir / "training_report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_scheduler(torch: Any, optimizer: Any, scheduler_name: str, epochs: int) -> Any:
    if scheduler_name == "none":
        return None
    if scheduler_name == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=max(epochs, 1),
        )
    raise TrainingRuntimeError(f"Unsupported scheduler: {scheduler_name}")


def _move_targets(targets: dict[str, Any], device: Any) -> dict[str, Any]:
    moved: dict[str, Any] = {}
    for key, value in targets.items():
        moved[key] = value.to(device) if hasattr(value, "to") else value
    return moved


def _run_epoch(
    *,
    model: Any,
    loader: Any,
    optimizer: Any,
    scaler: Any,
    device: Any,
    amp: bool,
    gradient_accumulation_steps: int,
) -> float:
    import torch

    model.train()
    total = 0.0
    batches = 0
    optimizer.zero_grad(set_to_none=True)
    for step, (images, targets) in enumerate(loader, start=1):
        images = images.to(device)
        targets = _move_targets(targets, device)
        with torch.autocast(
            device_type=device.type,
            enabled=amp and device.type == "cuda",
        ):
            outputs = model(images)
            loss, metrics = compute_multitask_loss(outputs, targets)
            loss = loss / max(gradient_accumulation_steps, 1)
        scaler.scale(loss).backward()
        if step % max(gradient_accumulation_steps, 1) == 0:
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
        total += metrics["loss"]
        batches += 1
    if batches % max(gradient_accumulation_steps, 1) != 0:
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)
    return round(total / max(batches, 1), 6)


def _validate_epoch(
    *,
    model: Any,
    loader: Any,
    device: Any,
    amp: bool,
) -> float:
    import torch

    model.eval()
    total = 0.0
    batches = 0
    with torch.no_grad():
        for images, targets in loader:
            images = images.to(device)
            targets = _move_targets(targets, device)
            with torch.autocast(
                device_type=device.type,
                enabled=amp and device.type == "cuda",
            ):
                outputs = model(images)
                _, metrics = compute_multitask_loss(outputs, targets)
            total += metrics["loss"]
            batches += 1
    return round(total / max(batches, 1), 6)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Train glass_500ml_v1 profile model.")
    parser.add_argument("--datasets-root", default="/datasets")
    parser.add_argument(
        "--config",
        default=str(
            Path(__file__).resolve().parent
            / "configs"
            / "glass_500ml_v1_training.json"
        ),
    )
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    args = parser.parse_args()

    config = TrainingConfig.from_json_file(Path(args.config))
    report = run_training(
        datasets_root=Path(args.datasets_root),
        config=config,
        audit_only=args.audit_only,
        allow_cpu=args.allow_cpu,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    _main()
