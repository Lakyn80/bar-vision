from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BottleProfileCreate(BaseModel):
    product_id: UUID
    version: str = Field(min_length=1, max_length=50)
    canonical_width: int = Field(gt=0, le=10_000)
    canonical_height: int = Field(gt=0, le=10_000)
    bottle_contour_data: dict[str, Any] | None = None
    anchor_points_json: dict[str, Any] | None = None
    liquid_roi_json: dict[str, Any] | None = None
    label_mask_json: dict[str, Any] | None = None
    active: bool = True


class BottleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    version: str
    canonical_width: int
    canonical_height: int
    reference_image_key: str | None
    reference_mask_key: str | None
    bottle_contour_data: dict[str, Any] | None
    anchor_points_json: dict[str, Any] | None
    liquid_roi_json: dict[str, Any] | None
    label_mask_json: dict[str, Any] | None
    active: bool
