"""add analytics event processing

Revision ID: b20c30d40e47
Revises: a10b20c30d45
Create Date: 2026-10-27 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "b20c30d40e47"
down_revision: str | Sequence[str] | None = "a10b20c30d45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_processed_events",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.add_column(
        "platform_period_metrics",
        sa.Column("reviews_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("platform_period_metrics", "reviews_count")
    op.drop_table("analytics_processed_events")
