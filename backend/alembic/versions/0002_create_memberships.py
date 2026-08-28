"""Create business memberships.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_memberships",
        sa.Column(
            "user_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "business_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            server_default="member",
            nullable=False,
        ),
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "business_id",
            name="uq_business_memberships_user_business",
        ),
    )

    op.create_index(
        "ix_business_memberships_user_id",
        "business_memberships",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_business_memberships_business_id",
        "business_memberships",
        ["business_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_memberships_business_id",
        table_name="business_memberships",
    )
    op.drop_index(
        "ix_business_memberships_user_id",
        table_name="business_memberships",
    )
    op.drop_table("business_memberships")
