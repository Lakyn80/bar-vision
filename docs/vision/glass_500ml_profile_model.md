# glass_500ml_v1 PyTorch profile model

This module is the required PyTorch transfer-learning path for exact
`glass_500ml_v1` recognition before calibrated measurement.

It deliberately separates responsibilities:

```text
PyTorch fine-tuning -> glass mask, bbox, profile score, landmarks
ONNX Runtime CPU    -> production perception inference
OpenCV              -> deterministic geometry and canonicalization
Liquid detector     -> normalized liquid level
Calibration engine  -> deterministic milliliters
```

The model must never predict milliliters directly.

## Backend modules

```text
backend/app/vision/glass_profile/
  schema.py           portable annotation format and validation
  dataset.py          audit, deterministic split, PyTorch Dataset
  model.py            TorchVision MobileNetV3 transfer model with geometry heads
  train.py            reproducible fine-tuning/checkpointing entrypoint
  evaluate.py         ready-gate and acceptance report metrics
  export_onnx.py      checkpoint -> ONNX + metadata export
  inference.py        ONNX Runtime CPU detector
  geometry.py         deterministic READY gate over model geometry
```

## Current Dataset State

Current local data:

```text
datasets/raw/glass_500ml_v1/
datasets/annotations/glass_500ml_v1/v1.json
```

`v1.json` contains 8 positive calibration photos from 62.5 ml to 500 ml.
It does not contain negative examples, bbox annotations, masks, landmarks, or
capture session ids. It is therefore useful as calibration/regression evidence,
but not sufficient for supervised fine-tuning.

The deterministic split for the current calibration-only set is recorded in:

```text
datasets/splits/glass_500ml_v1/v1.json
```

Because session metadata is missing, this split is not proof of leakage-safe ML
evaluation. Future capture sets must include `capture_session_id` and split by
session.

## Required Annotation Format

The required geometry-aware schema is:

```text
datasets/annotations/glass_500ml_v1/annotation_schema_v2.json
```

Every positive `valid_glass` sample needs:

- normalized bbox `[x1, y1, x2, y2]`
- glass mask, either polygon or mask file
- keypoints: `rim_left`, `rim_right`, `bottom_left`, `bottom_right`,
  `rim_center`, `bottom_center`

Negative examples are required and must include wrong glasses, cups, bottles,
background/no-object frames, partial/cropped glasses, severe rotation,
bad perspective, too-far, and too-close frames.

## Commands

The default training config uses photometric augmentation only: brightness,
contrast, minor blur, and sensor noise. Geometric augmentation must transform
bbox, mask, and keypoints together before it is enabled.

Audit the current dataset:

```powershell
docker compose exec -T backend python -m app.vision.glass_profile.dataset `
  --datasets-root /datasets `
  --annotation annotations/glass_500ml_v1/v1.json `
  --inspect-images
```

Audit with the training config without requiring Torch:

```powershell
docker compose exec -T backend python -m app.vision.glass_profile.train `
  --datasets-root /datasets `
  --audit-only
```

Build the GPU training image when CUDA PyTorch training is needed:

```powershell
docker build -f backend/Dockerfile.training -t bar-vision-training backend
```

Dependency layout:

- production backend uses `uv sync --frozen` from `backend/uv.lock` in Python
  3.13 and serves only ONNX Runtime CPU inference
- the CUDA training image uses the official PyTorch CUDA 12.6 runtime and
  installs the extra training/export tools with `uv pip install`, because that
  image currently provides its own CUDA-enabled Python/PyTorch stack

Run training with NVIDIA runtime:

```powershell
docker run --rm --gpus all `
  -v ${PWD}/datasets:/datasets:ro `
  -v ${PWD}/models:/app/models `
  bar-vision-training
```

Export a validated checkpoint to ONNX:

```powershell
docker run --rm `
  -v ${PWD}/models:/app/models `
  bar-vision-training `
  python -m app.vision.glass_profile.export_onnx `
    --checkpoint models/glass_profile/glass_500ml_v1/best.pt `
    --output models/glass_profile/glass_500ml_v1.onnx `
    --metadata models/glass_profile/glass_500ml_v1.metadata.json
```

Production inference uses ONNX Runtime CPU from the backend. The compose stack
mounts `./models` read-only into `/models`.

## Acceptance Report

The ONNX metadata file must keep `accepted_for_production: false` until a real
test-set report has measured:

- segmentation IoU/Dice/precision/recall
- keypoint error
- false READY rate
- false rejection rate
- PyTorch/ONNX parity
- ONNX CPU mean/median/P95 latency
- model size and CPU thread settings

The backend READY gate refuses unvalidated model metadata.
