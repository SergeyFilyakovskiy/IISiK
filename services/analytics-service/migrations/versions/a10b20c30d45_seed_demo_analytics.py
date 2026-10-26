"""seed demo analytics

Revision ID: a10b20c30d45
Revises: 0765c196609c
Create Date: 2026-10-26 17:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a10b20c30d45"
down_revision: str | Sequence[str] | None = "0765c196609c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO teacher_period_metrics "
            "(teacher_id, period_date, lessons_completed, revenue, avg_rating, "
            "reviews_count, updated_at) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000004', DATE '2026-10-01', "
            "1, 25, 5, 1, DEFAULT) "
            "ON CONFLICT DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO platform_period_metrics "
            "(period_date, lessons_completed, bookings_created, revenue, avg_rating, "
            "active_students, active_teachers, updated_at) "
            "VALUES "
            "(DATE '2026-10-01', 1, 1, 25, 5, 1, 1, DEFAULT) "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM teacher_period_metrics "
            "WHERE teacher_id = '00000000-0000-0000-0000-000000000004' "
            "AND period_date = DATE '2026-10-01'"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM platform_period_metrics "
            "WHERE period_date = DATE '2026-10-01' "
            "AND lessons_completed = 1 AND bookings_created = 1 "
            "AND revenue = 25 AND avg_rating = 5 "
            "AND active_students = 1 AND active_teachers = 1"
        )
    )
