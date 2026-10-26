"""seed catalog

Revision ID: b7a1c4e20d51
Revises: ce91d7cc06ec
Create Date: 2026-10-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7a1c4e20d51"
down_revision: str | Sequence[str] | None = "ce91d7cc06ec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TEACHER_USER_ID = "00000000-0000-0000-0000-000000000003"
TEACHER_ID = "00000000-0000-0000-0000-000000000004"
SUBJECT_ID = "00000000-0000-0000-0000-000000000010"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO subjects (id, name, is_active)
            VALUES ('{SUBJECT_ID}', 'Mathematics', TRUE)
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO teachers (
                id, user_id, experience_years, price_per_lesson, currency, profile_status
            )
            VALUES (
                '{TEACHER_ID}', '{TEACHER_USER_ID}', 5, 25.00, 'BYN', 'ACTIVE'
            )
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO teacher_subjects (teacher_id, subject_id, proficiency_level)
            VALUES ('{TEACHER_ID}', '{SUBJECT_ID}', 'advanced')
            ON CONFLICT DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            INSERT INTO teacher_rating_cache (teacher_id, avg_rating, reviews_count)
            VALUES ('{TEACHER_ID}', 4.50, 1)
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM teacher_rating_cache WHERE teacher_id = '{TEACHER_ID}'"))
    op.execute(
        sa.text(
            f"""
            DELETE FROM teacher_subjects
            WHERE teacher_id = '{TEACHER_ID}' AND subject_id = '{SUBJECT_ID}'
            """
        )
    )
    op.execute(
        sa.text(f"DELETE FROM teachers WHERE id = '{TEACHER_ID}' AND user_id = '{TEACHER_USER_ID}'")
    )
    op.execute(sa.text(f"DELETE FROM subjects WHERE id = '{SUBJECT_ID}' AND name = 'Mathematics'"))
