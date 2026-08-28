from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VenueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    name: str
    timezone: str
    active: bool
