"""seed demo notification

Revision ID: a10b20c30d44
Revises: 4733086e94cc
Create Date: 2026-10-26 17:45:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a10b20c30d44"
down_revision: str | Sequence[str] | None = "4733086e94cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO notifications "
            "(id, user_id, event_type, title, body, status, source_event_id, "
            "created_at, sent_at) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000070', "
            "'00000000-0000-0000-0000-000000000001', "
            "'LessonCompleted', 'Lesson completed', 'Lesson completed successfully', "
            "'CREATED', '00000000-0000-0000-0000-000000000030', DEFAULT, NULL) "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM notifications "
            "WHERE id = '00000000-0000-0000-0000-000000000070'"
        )
    )
