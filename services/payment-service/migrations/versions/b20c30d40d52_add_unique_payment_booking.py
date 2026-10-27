"""add unique payment booking

Revision ID: b20c30d40d52
Revises: a10b20c30d42
Create Date: 2026-10-27 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b20c30d40d52"
down_revision: str | Sequence[str] | None = "a10b20c30d42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint("uq_payments_booking_id", "payments", ["booking_id"])


def downgrade() -> None:
    op.drop_constraint("uq_payments_booking_id", "payments", type_="unique")
