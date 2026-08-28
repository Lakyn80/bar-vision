from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    business_id: UUID
    name: str = Field(min_length=1, max_length=255)
    brand: str = Field(min_length=1, max_length=255)
    nominal_volume_ml: int = Field(gt=0, le=100_000)
    barcode: str | None = Field(default=None, max_length=64)
    active: bool = True


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    name: str
    brand: str
    nominal_volume_ml: int
    barcode: str | None
    active: bool
