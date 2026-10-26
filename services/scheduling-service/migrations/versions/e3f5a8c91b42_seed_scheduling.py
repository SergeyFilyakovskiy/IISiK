"""seed scheduling

Revision ID: e3f5a8c91b42
Revises: 88a4e00c273e
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f5a8c91b42"
down_revision: str | Sequence[str] | None = "88a4e00c273e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TEACHER_ID = "00000000-0000-0000-0000-000000000004"
SUBJECT_ID = "00000000-0000-0000-0000-000000000010"
SCHEDULE_SLOT_ID = "00000000-0000-0000-0000-000000000020"
LESSON_ID = "00000000-0000-0000-0000-000000000030"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO schedule_slots (
                id, teacher_id, weekday, start_time, end_time, is_active
            )
            VALUES (
                '{SCHEDULE_SLOT_ID}', '{TEACHER_ID}', 1, '10:00', '12:00', TRUE
            )
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO lessons (
                id, teacher_id, subject_id, schedule_slot_id, start_at,
                duration_minutes, status, price, currency
            )
            VALUES (
                '{LESSON_ID}', '{TEACHER_ID}', '{SUBJECT_ID}', '{SCHEDULE_SLOT_ID}',
                '2026-11-02 10:00:00+00', 60, 'AVAILABLE', 25.00, 'BYN'
            )
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM lessons WHERE id = '{LESSON_ID}'"))
    op.execute(sa.text(f"DELETE FROM schedule_slots WHERE id = '{SCHEDULE_SLOT_ID}'"))
