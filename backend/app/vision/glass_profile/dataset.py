from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import cv2
import numpy as np

from app.vision.glass_profile.schema import (
    GLASS_500ML_PROFILE_KEY,
    KEYPOINT_NAMES,
    GlassMaskAnnotation,
    GlassProfileAnnotationDocument,
    GlassProfileAnnotationError,
    GlassProfileSample,
    load_glass_profile_annotations,
)


@dataclass(frozen=True, slots=True)
class ImageShapeSummary:
    image: str
    width: int
    height: int
    channels: int


@dataclass(frozen=True, slots=True)
class DatasetAuditResult:
    dataset_id: str
    dataset_version: str
    schema_version: str
    total_samples: int
    positive_samples: int
    negative_samples: int
    samples_with_bbox: int
    samples_with_mask: int
    samples_with_keypoints: int
    missing_session_metadata: int
    image_shapes: tuple[ImageShapeSummary, ...]
    ready_for_fine_tuning: bool
    blocking_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["image_shapes"] = [asdict(item) for item in self.image_shapes]
        return payload


@dataclass(frozen=True, slots=True)
class SplitManifest:
    dataset_id: str
    dataset_version: str
    split_version: str
    seed: int
    strategy: str
    train: tuple[str, ...]
    validation: tuple[str, ...]
    test: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_glass_profile_dataset(
    document: GlassProfileAnnotationDocument,
    *,
    inspect_images: bool = False,
) -> DatasetAuditResult:
    positives = [sample for sample in document.samples if sample.is_positive]
    negatives = [sample for sample in document.samples if sample.is_negative]
    samples_with_bbox = sum(1 for sample in document.samples if sample.has_bbox)
    samples_with_mask = sum(1 for sample in document.samples if sample.has_mask)
    samples_with_keypoints = sum(
        1 for sample in document.samples if sample.has_required_keypoints
    )
    missing_session = sum(
        1 for sample in document.samples if not sample.capture_session_id
    )

    image_shapes: list[ImageShapeSummary] = []
    if inspect_images:
        for sample in document.samples:
            image = cv2.imread(str(sample.image_path), cv2.IMREAD_UNCHANGED)
            if image is None:
                image_shapes.append(
                    ImageShapeSummary(
                        image=sample.image,
                        width=0,
                        height=0,
                        channels=0,
                    )
                )
                continue
            height, width = image.shape[:2]
            channels = image.shape[2] if image.ndim == 3 else 1
            image_shapes.append(
                ImageShapeSummary(
                    image=sample.image,
                    width=int(width),
                    height=int(height),
                    channels=int(channels),
                )
            )

    blocking: list[str] = []
    if document.profile_key != GLASS_500ML_PROFILE_KEY:
        blocking.append("dataset profile_key is not glass_500ml_v1")
    if not positives:
        blocking.append("no positive valid_glass samples")
    if not negatives:
        blocking.append("negative examples are missing")
    if any(not sample.has_bbox for sample in positives):
        blocking.append("positive samples missing normalized bbox annotations")
    if any(not sample.has_mask for sample in positives):
        blocking.append("positive samples missing glass mask annotations")
    if any(not sample.has_required_keypoints for sample in positives):
        blocking.append("positive samples missing required glass keypoints")
    if len(document.samples) < 3:
        blocking.append("at least train/validation/test samples are required")

    return DatasetAuditResult(
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        schema_version=document.schema_version,
        total_samples=len(document.samples),
        positive_samples=len(positives),
        negative_samples=len(negatives),
        samples_with_bbox=samples_with_bbox,
        samples_with_mask=samples_with_mask,
        samples_with_keypoints=samples_with_keypoints,
        missing_session_metadata=missing_session,
        image_shapes=tuple(image_shapes),
        ready_for_fine_tuning=not blocking,
        blocking_reasons=tuple(blocking),
    )


def create_deterministic_split(
    samples: Sequence[GlassProfileSample],
    *,
    dataset_id: str,
    dataset_version: str,
    seed: int,
    split_version: str | None = None,
) -> SplitManifest:
    if not samples:
        raise GlassProfileAnnotationError("Cannot split an empty dataset.")

    groups: dict[str, list[GlassProfileSample]] = {}
    missing_session = 0
    for sample in samples:
        if not sample.capture_session_id:
            missing_session += 1
        groups.setdefault(sample.split_group, []).append(sample)

    ordered_groups = sorted(
        groups.items(),
        key=lambda item: _stable_group_value(item[0], seed=seed),
    )

    train: list[str] = []
    validation: list[str] = []
    test: list[str] = []
    group_count = len(ordered_groups)
    train_cut = max(1, round(group_count * 0.7))
    val_cut = max(train_cut + 1, round(group_count * 0.85))
    if group_count >= 3:
        train_cut = min(train_cut, group_count - 2)
        val_cut = min(max(val_cut, train_cut + 1), group_count - 1)

    for index, (_, group_samples) in enumerate(ordered_groups):
        destination = (
            train
            if index < train_cut
            else validation
            if index < val_cut
            else test
        )
        destination.extend(sample.image for sample in group_samples)

    warnings: list[str] = []
    if missing_session:
        warnings.append(
            "capture_session_id missing for "
            f"{missing_session} samples; split_group fell back to image filename"
        )
    if not validation or not test:
        warnings.append("dataset too small for non-empty validation and test splits")

    return SplitManifest(
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        split_version=(
            split_version
            or f"{dataset_id}-{dataset_version}-seed-{seed}"
        ),
        seed=seed,
        strategy=(
            "deterministic hash by split_group; capture_session_id should be "
            "used as split_group when frames share a capture session"
        ),
        train=tuple(sorted(train)),
        validation=tuple(sorted(validation)),
        test=tuple(sorted(test)),
        warnings=tuple(warnings),
    )


class GlassProfileTorchDataset:
    """
    PyTorch dataset for the single-instance glass geometry model.

    Targets are normalized and portable: bbox xyxy, fixed keypoint order, and
    a binary glass mask. Torch is imported lazily so dataset audits can run in
    the lightweight production backend image.
    """

    def __init__(
        self,
        samples: Sequence[GlassProfileSample],
        *,
        input_size: tuple[int, int],
        mask_size: int,
        require_geometry: bool = True,
        allow_bbox_mask_fallback: bool = False,
        augmentation: dict[str, float] | None = None,
    ) -> None:
        import torch

        self._torch = torch
        self.samples = tuple(samples)
        self.input_size = input_size
        self.mask_size = mask_size
        self.allow_bbox_mask_fallback = allow_bbox_mask_fallback
        self.augmentation = augmentation or {}
        if require_geometry:
            self._validate_training_samples()

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[Any, dict[str, Any]]:
        sample = self.samples[index]
        image_bgr = cv2.imread(str(sample.image_path), cv2.IMREAD_COLOR)
        if image_bgr is None:
            raise GlassProfileAnnotationError(f"Could not read image {sample.image}.")

        input_width, input_height = self.input_size
        image_bgr = cv2.resize(
            image_bgr,
            (input_width, input_height),
            interpolation=cv2.INTER_AREA,
        )
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        image_rgb = _apply_photometric_augmentation(
            image_rgb,
            self.augmentation,
        )
        image = self._torch.from_numpy(
            np.transpose(image_rgb, (2, 0, 1)).astype(np.float32) / 255.0
        )

        target = {
            "profile_label": self._torch.tensor(
                1 if sample.is_positive else 0,
                dtype=self._torch.long,
            ),
            "bbox": self._torch.tensor(
                sample.bbox_norm or (0.0, 0.0, 0.0, 0.0),
                dtype=self._torch.float32,
            ),
            "keypoints": self._torch.tensor(
                _keypoints_tensor(sample),
                dtype=self._torch.float32,
            ),
            "mask": self._torch.from_numpy(
                _mask_array(
                    sample=sample,
                    raw_dir=sample.image_path.parent,
                    mask_size=self.mask_size,
                    allow_bbox_mask_fallback=self.allow_bbox_mask_fallback,
                )
            ).unsqueeze(0),
            "is_positive": self._torch.tensor(sample.is_positive),
            "image": sample.image,
        }
        return image, target

    def _validate_training_samples(self) -> None:
        if not self.samples:
            raise GlassProfileAnnotationError("Training dataset is empty.")
        positives = [sample for sample in self.samples if sample.is_positive]
        negatives = [sample for sample in self.samples if sample.is_negative]
        if not positives:
            raise GlassProfileAnnotationError("Training requires positive samples.")
        if not negatives:
            raise GlassProfileAnnotationError("Training requires negative examples.")
        for sample in positives:
            if not sample.bbox_norm:
                raise GlassProfileAnnotationError(
                    f"{sample.image} is missing bbox annotation."
                )
            if not sample.has_required_keypoints:
                raise GlassProfileAnnotationError(
                    f"{sample.image} is missing required keypoints."
                )
            if not sample.mask and not self.allow_bbox_mask_fallback:
                raise GlassProfileAnnotationError(
                    f"{sample.image} is missing glass mask annotation."
                )


def collate_glass_profile_batch(
    batch: Sequence[tuple[Any, dict[str, Any]]],
) -> tuple[Any, dict[str, Any]]:
    import torch

    images = torch.stack([item[0] for item in batch])
    targets: dict[str, Any] = {}
    keys = batch[0][1].keys()
    for key in keys:
        values = [item[1][key] for item in batch]
        if key == "image":
            targets[key] = values
        else:
            targets[key] = torch.stack(values)
    return images, targets


def samples_for_images(
    samples: Iterable[GlassProfileSample],
    image_names: Iterable[str],
) -> tuple[GlassProfileSample, ...]:
    wanted = set(image_names)
    return tuple(sample for sample in samples if sample.image in wanted)


def _stable_group_value(group: str, *, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{group}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _keypoints_tensor(sample: GlassProfileSample) -> np.ndarray:
    keypoints = np.zeros((len(KEYPOINT_NAMES), 3), dtype=np.float32)
    for index, name in enumerate(KEYPOINT_NAMES):
        if name in sample.keypoints_norm:
            keypoints[index] = np.array(sample.keypoints_norm[name], dtype=np.float32)
    return keypoints


def _mask_array(
    *,
    sample: GlassProfileSample,
    raw_dir: Path,
    mask_size: int,
    allow_bbox_mask_fallback: bool,
) -> np.ndarray:
    mask = np.zeros((mask_size, mask_size), dtype=np.float32)
    if sample.mask:
        return _load_mask_annotation(
            sample.mask,
            raw_dir=raw_dir,
            mask_size=mask_size,
        )
    if allow_bbox_mask_fallback and sample.bbox_norm:
        x1, y1, x2, y2 = sample.bbox_norm
        cv2.rectangle(
            mask,
            (int(x1 * mask_size), int(y1 * mask_size)),
            (int(x2 * mask_size), int(y2 * mask_size)),
            color=1.0,
            thickness=-1,
        )
    return mask


def _load_mask_annotation(
    mask_annotation: GlassMaskAnnotation,
    *,
    raw_dir: Path,
    mask_size: int,
) -> np.ndarray:
    if mask_annotation.kind == "polygon":
        if not mask_annotation.points:
            return np.zeros((mask_size, mask_size), dtype=np.float32)
        points = np.array(
            [
                [int(x * mask_size), int(y * mask_size)]
                for x, y in mask_annotation.points
            ],
            dtype=np.int32,
        )
        mask = np.zeros((mask_size, mask_size), dtype=np.float32)
        cv2.fillPoly(mask, [points], 1.0)
        return mask

    if mask_annotation.kind == "file" and mask_annotation.path:
        mask_path = raw_dir / mask_annotation.path
        raw = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if raw is None:
            raise GlassProfileAnnotationError("Mask image could not be read.")
        resized = cv2.resize(
            raw,
            (mask_size, mask_size),
            interpolation=cv2.INTER_NEAREST,
        )
        return (resized > 127).astype(np.float32)

    return np.zeros((mask_size, mask_size), dtype=np.float32)


def _apply_photometric_augmentation(
    image_rgb: np.ndarray,
    augmentation: dict[str, float],
) -> np.ndarray:
    if not augmentation:
        return image_rgb

    image = image_rgb.astype(np.float32) / 255.0
    brightness = float(augmentation.get("brightness") or 0.0)
    if brightness > 0:
        image = image + np.random.uniform(-brightness, brightness)

    contrast = float(augmentation.get("contrast") or 0.0)
    if contrast > 0:
        factor = 1.0 + np.random.uniform(-contrast, contrast)
        mean = np.mean(image, axis=(0, 1), keepdims=True)
        image = (image - mean) * factor + mean

    noise_std = float(augmentation.get("noise_std") or 0.0)
    if noise_std > 0:
        image = image + np.random.normal(0.0, noise_std, size=image.shape)

    image = np.clip(image, 0.0, 1.0)

    blur_probability = float(augmentation.get("blur_probability") or 0.0)
    if blur_probability > 0 and np.random.random() < blur_probability:
        image = cv2.GaussianBlur(image, (3, 3), 0)

    return (np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit and split glass_500ml_v1 profile annotations."
    )
    parser.add_argument("--datasets-root", default="/datasets")
    parser.add_argument(
        "--annotation",
        default="annotations/glass_500ml_v1/v1.json",
    )
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument("--inspect-images", action="store_true")
    parser.add_argument("--write-split")
    args = parser.parse_args()

    document = load_glass_profile_annotations(
        datasets_root=Path(args.datasets_root),
        annotation_relative_path=args.annotation,
    )
    audit = audit_glass_profile_dataset(
        document,
        inspect_images=args.inspect_images,
    )
    split = create_deterministic_split(
        document.samples,
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        seed=args.seed,
    )
    report = {
        "audit": audit.to_dict(),
        "split": split.to_dict(),
    }
    print(json.dumps(report, indent=2))
    if args.write_split:
        output = Path(args.write_split)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(split.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    _main()
