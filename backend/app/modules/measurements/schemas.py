from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    measurement_type: str
    original_image_key: str | None
    bottle_profile_id: UUID | None
    product_id: UUID | None
    created_by: UUID
