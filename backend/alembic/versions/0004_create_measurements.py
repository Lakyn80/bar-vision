"""Create measurements table.

Revision ID: 0004
Revises: 0003
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "measurements",
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "measurement_type",
            sa.String(length=32),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column("shift_id", sa.Uuid(), nullable=True),
        sa.Column("bottle_instance_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("bottle_profile_id", sa.Uuid(), nullable=True),
        sa.Column("calibration_version_id", sa.Uuid(), nullable=True),
        sa.Column("volume_ml", sa.Integer(), nullable=True),
        sa.Column("liquid_level_normalized", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("alignment_score", sa.Float(), nullable=True),
        sa.Column("level_score", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("original_image_key", sa.String(length=512), nullable=True),
        sa.Column("canonical_image_key", sa.String(length=512), nullable=True),
        sa.Column("debug_image_key", sa.String(length=512), nullable=True),
        sa.Column("vision_version", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bottle_instance_id"],
            ["bottle_instances.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["bottle_profile_id"],
            ["bottle_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["calibration_version_id"],
            ["calibration_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_measurements_shift_id",
        "measurements",
        ["shift_id"],
        unique=False,
    )
    op.create_index(
        "ix_measurements_bottle_instance_id",
        "measurements",
        ["bottle_instance_id"],
        unique=False,
    )
    op.create_index(
        "ix_measurements_product_id",
        "measurements",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_measurements_bottle_profile_id",
        "measurements",
        ["bottle_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_measurements_calibration_version_id",
        "measurements",
        ["calibration_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_measurements_created_by",
        "measurements",
        ["created_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_measurements_created_by", table_name="measurements")
    op.drop_index(
        "ix_measurements_calibration_version_id",
        table_name="measurements",
    )
    op.drop_index(
        "ix_measurements_bottle_profile_id",
        table_name="measurements",
    )
    op.drop_index("ix_measurements_product_id", table_name="measurements")
    op.drop_index(
        "ix_measurements_bottle_instance_id",
        table_name="measurements",
    )
    op.drop_index("ix_measurements_shift_id", table_name="measurements")
    op.drop_table("measurements")
