"""Create products and bottle profile tables.

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("nominal_volume_ml", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
            ["business_id"],
            ["businesses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_products_business_id",
        "products",
        ["business_id"],
        unique=False,
    )

    op.create_table(
        "bottle_profiles",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("canonical_width", sa.Integer(), nullable=False),
        sa.Column("canonical_height", sa.Integer(), nullable=False),
        sa.Column("reference_image_key", sa.String(length=512), nullable=True),
        sa.Column("reference_mask_key", sa.String(length=512), nullable=True),
        sa.Column(
            "bottle_contour_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "anchor_points_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "liquid_roi_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "label_mask_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bottle_profiles_product_id",
        "bottle_profiles",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "calibration_versions",
        sa.Column("bottle_profile_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("calibration_method", sa.String(length=100), nullable=False),
        sa.Column(
            "calibration_points_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("algorithm_version", sa.String(length=50), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
            ["bottle_profile_id"],
            ["bottle_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calibration_versions_bottle_profile_id",
        "calibration_versions",
        ["bottle_profile_id"],
        unique=False,
    )

    op.create_table(
        "bottle_instances",
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("bottle_profile_id", sa.Uuid(), nullable=False),
        sa.Column("internal_code", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["bottle_profile_id"],
            ["bottle_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["venue_id"],
            ["venues.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bottle_instances_venue_id",
        "bottle_instances",
        ["venue_id"],
        unique=False,
    )
    op.create_index(
        "ix_bottle_instances_product_id",
        "bottle_instances",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_bottle_instances_bottle_profile_id",
        "bottle_instances",
        ["bottle_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bottle_instances_bottle_profile_id",
        table_name="bottle_instances",
    )
    op.drop_index(
        "ix_bottle_instances_product_id",
        table_name="bottle_instances",
    )
    op.drop_index(
        "ix_bottle_instances_venue_id",
        table_name="bottle_instances",
    )
    op.drop_table("bottle_instances")

    op.drop_index(
        "ix_calibration_versions_bottle_profile_id",
        table_name="calibration_versions",
    )
    op.drop_table("calibration_versions")

    op.drop_index(
        "ix_bottle_profiles_product_id",
        table_name="bottle_profiles",
    )
    op.drop_table("bottle_profiles")

    op.drop_index("ix_products_business_id", table_name="products")
    op.drop_table("products")
