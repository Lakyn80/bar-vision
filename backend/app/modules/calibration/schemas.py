from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CalibrationPointInput(BaseModel):
    true_ml: float = Field(ge=0, le=10_000)
    image: str = Field(min_length=1, max_length=255)
    level_normalized: float | None = Field(default=None, ge=0, le=1)
    capture_metadata: dict[str, Any] = Field(default_factory=dict)
    image_key: str | None = None

    @field_validator("image")
    @classmethod
    def reject_path_traversal(cls, value: str) -> str:
        cleaned = value.replace("\\", "/")
        if (
            cleaned.startswith("/")
            or ".." in cleaned.split("/")
            or cleaned.count("/") > 0
        ):
            raise ValueError("Image must be a plain filename.")
        return cleaned


class CalibrationDatasetPayload(BaseModel):
    """Ground-truth package attached to one CalibrationVersion."""

    dataset_id: str = Field(min_length=1, max_length=100)
    dataset_version: str = Field(min_length=1, max_length=50)
    vessel: str | None = Field(default=None, max_length=100)
    nominal_volume_ml: int | None = Field(default=None, gt=0, le=10_000)
    step_ml: float | None = Field(default=None, gt=0, le=10_000)
    interpolation_method: str = Field(
        default="pchip",
        pattern="^(cylindrical_linear|pchip)$",
    )
    notes: str | None = None
    points: list[CalibrationPointInput] = Field(min_length=1)

    @field_validator("points")
    @classmethod
    def require_unique_images(
        cls,
        points: list[CalibrationPointInput],
    ) -> list[CalibrationPointInput]:
        names = [point.image for point in points]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate image filenames in calibration points.")
        mls = [point.true_ml for point in points]
        if len(mls) != len(set(mls)):
            raise ValueError("Duplicate true_ml values in calibration points.")
        return points


class CalibrationVersionCreate(BaseModel):
    bottle_profile_id: UUID
    version: str = Field(min_length=1, max_length=50)
    calibration_method: str = Field(min_length=1, max_length=100)
    algorithm_version: str = Field(min_length=1, max_length=50)
    active: bool = True
    dataset: CalibrationDatasetPayload


class CalibrationVersionUpdate(BaseModel):
    """Edit metadata / ground-truth labels. Prefer new version for major changes."""

    version: str | None = Field(default=None, min_length=1, max_length=50)
    calibration_method: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    algorithm_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    active: bool | None = None
    dataset: CalibrationDatasetPayload | None = None


class CalibrationVersionFromDatasetCreate(BaseModel):
    bottle_profile_id: UUID
    version: str = Field(min_length=1, max_length=50)
    calibration_method: str = Field(
        default="physical_measured_pour",
        min_length=1,
        max_length=100,
    )
    algorithm_version: str = Field(
        default="dataset-package-v1",
        min_length=1,
        max_length=50,
    )
    active: bool = True
    annotation_relative_path: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Path under DATASETS_ROOT, e.g. "
            "annotations/glass_500ml_v1/v1.json"
        ),
    )


class CalibrationVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bottle_profile_id: UUID
    version: str
    calibration_method: str
    algorithm_version: str
    active: bool
    calibration_points_json: dict[str, Any]


class VolumeEvaluateRequest(BaseModel):
    level_normalized: float = Field(
        description="0 = empty/bottom, 1 = full mark",
    )


class VolumeEvaluateResponse(BaseModel):
    calibration_version_id: UUID
    volume_ml: float
    level_normalized: float
    method: str
    clamped: bool
    in_calibration_range: bool
