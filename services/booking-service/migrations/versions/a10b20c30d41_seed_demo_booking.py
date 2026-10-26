"""seed demo booking

Revision ID: a10b20c30d41
Revises: 8078afc61aa3
Create Date: 2026-10-26 17:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a10b20c30d41"
down_revision: str | Sequence[str] | None = "8078afc61aa3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO bookings "
            "(id, lesson_id, student_id, teacher_id, subject_id, status, price, currency, "
            "created_at, updated_at, paid_at, completed_at, cancelled_at, cancel_reason) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000040', "
            "'00000000-0000-0000-0000-000000000030', "
            "'00000000-0000-0000-0000-000000000002', "
            "'00000000-0000-0000-0000-000000000004', "
            "'00000000-0000-0000-0000-000000000010', "
            "'COMPLETED', 25, 'BYN', DEFAULT, DEFAULT, "
            "TIMESTAMPTZ '2026-10-20 12:00:00+00', "
            "TIMESTAMPTZ '2026-10-20 12:00:00+00', NULL, NULL) "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM bookings "
            "WHERE id = '00000000-0000-0000-0000-000000000040'"
        )
    )
