"""add notification source uniqueness

Revision ID: b20c30d40e46
Revises: a10b20c30d44
Create Date: 2026-10-27 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = "b20c30d40e46"
down_revision: str | Sequence[str] | None = "a10b20c30d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_notifications_event_type_source_event_id",
        "notifications",
        ["event_type", "source_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notifications_event_type_source_event_id",
        "notifications",
        type_="unique",
    )
