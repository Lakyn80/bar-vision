import pytest


def test_multitask_model_forward_and_loss_smoke() -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("torchvision")

    from app.vision.glass_profile.model import (
        GlassGeometryModelConfig,
        build_glass_geometry_model,
        compute_multitask_loss,
    )

    config = GlassGeometryModelConfig(
        input_width=64,
        input_height=64,
        mask_size=16,
        pretrained_backbone=False,
        dropout=0.0,
    )
    model = build_glass_geometry_model(config)
    images = torch.rand((2, 3, 64, 64), dtype=torch.float32)
    outputs = model(images)

    targets = {
        "profile_label": torch.tensor([1, 0], dtype=torch.long),
        "bbox": torch.tensor(
            [
                [0.30, 0.10, 0.70, 0.90],
                [0.0, 0.0, 0.0, 0.0],
            ],
            dtype=torch.float32,
        ),
        "keypoints": torch.ones((2, 6, 3), dtype=torch.float32) * 0.5,
        "mask": torch.zeros((2, 1, 16, 16), dtype=torch.float32),
    }
    targets["mask"][0, :, 4:14, 5:11] = 1.0

    loss, metrics = compute_multitask_loss(outputs, targets)
    loss.backward()

    assert torch.isfinite(loss)
    assert metrics["loss"] > 0
    assert outputs["profile_logits"].shape == (2, 2)
    assert outputs["bbox"].shape == (2, 4)
    assert outputs["keypoints"].shape == (2, 6, 3)
    assert outputs["mask_logits"].shape == (2, 1, 16, 16)
