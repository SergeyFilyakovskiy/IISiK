"""scope notification uniqueness by recipient

Revision ID: c30d40e46f51
Revises: b20c30d40e46
Create Date: 2026-11-05 00:00:00.000000

"""
from collections.abc import Sequence

from alembic import op


revision: str = "c30d40e46f51"
down_revision: str | Sequence[str] | None = "b20c30d40e46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_notifications_event_type_source_event_id", "notifications", type_="unique"
    )
    op.create_unique_constraint(
        "uq_notifications_user_event_source",
        "notifications",
        ["user_id", "event_type", "source_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_notifications_user_event_source", "notifications", type_="unique")
    op.create_unique_constraint(
        "uq_notifications_event_type_source_event_id",
        "notifications",
        ["event_type", "source_event_id"],
    )
