from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class BottleProfile(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "bottle_profiles"

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    canonical_width: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    canonical_height: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    reference_image_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    reference_mask_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    bottle_contour_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    anchor_points_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    liquid_roi_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    label_mask_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )


class BottleInstance(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "bottle_instances"

    venue_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    bottle_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bottle_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    internal_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class CalibrationVersion(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "calibration_versions"

    bottle_profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bottle_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    calibration_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    calibration_points_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    algorithm_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
