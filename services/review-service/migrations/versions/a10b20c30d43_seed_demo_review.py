"""seed demo review

Revision ID: a10b20c30d43
Revises: 7f39cfa88b59
Create Date: 2026-10-26 17:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a10b20c30d43"
down_revision: str | Sequence[str] | None = "7f39cfa88b59"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO reviews "
            "(id, lesson_id, student_id, teacher_id, rating, comment, created_at, updated_at) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000060', "
            "'00000000-0000-0000-0000-000000000030', "
            "'00000000-0000-0000-0000-000000000002', "
            "'00000000-0000-0000-0000-000000000004', "
            "5, 'Great lesson', TIMESTAMPTZ '2026-10-20 12:00:00+00', "
            "TIMESTAMPTZ '2026-10-20 12:00:00+00') "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM reviews "
            "WHERE id = '00000000-0000-0000-0000-000000000060'"
        )
    )
