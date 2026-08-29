from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    measurement_type: str
    original_image_key: str | None
    canonical_image_key: str | None = None
    debug_image_key: str | None = None
    alignment_score: float | None = None
    liquid_level_normalized: float | None = None
    level_score: float | None = None
    volume_ml: int | None = None
    vision_version: str | None = None
    bottle_profile_id: UUID | None
    product_id: UUID | None
    created_by: UUID
