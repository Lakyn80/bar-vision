from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Product(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "products"

    business_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    brand: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    nominal_volume_ml: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    barcode: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
