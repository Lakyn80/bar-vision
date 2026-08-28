from uuid import UUID

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Measurement(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "measurements"

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="draft",
        server_default="draft",
    )

    measurement_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",
        server_default="DRAFT",
    )

    shift_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )

    bottle_instance_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bottle_instances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    product_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    bottle_profile_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bottle_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    calibration_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("calibration_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    volume_ml: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    liquid_level_normalized: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    alignment_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    level_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    original_image_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    canonical_image_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    debug_image_key: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    vision_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_by: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
