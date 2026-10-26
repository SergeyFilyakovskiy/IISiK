"""seed demo payment

Revision ID: a10b20c30d42
Revises: c178afb50750
Create Date: 2026-10-26 17:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a10b20c30d42"
down_revision: str | Sequence[str] | None = "c178afb50750"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO payments "
            "(id, booking_id, student_id, teacher_id, amount, currency, payment_method, "
            "status, created_at, updated_at, paid_at, refunded_at, failure_reason, "
            "refund_reason) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000050', "
            "'00000000-0000-0000-0000-000000000040', "
            "'00000000-0000-0000-0000-000000000002', "
            "'00000000-0000-0000-0000-000000000004', "
            "25, 'BYN', 'CARD', 'SUCCEEDED', DEFAULT, DEFAULT, "
            "TIMESTAMPTZ '2026-10-20 12:00:00+00', NULL, NULL, NULL) "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM payments "
            "WHERE id = '00000000-0000-0000-0000-000000000050'"
        )
    )
