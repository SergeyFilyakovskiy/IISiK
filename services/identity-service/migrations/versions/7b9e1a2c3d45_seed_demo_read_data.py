"""seed demo read data

Revision ID: 7b9e1a2c3d45
Revises: 6a8d0c2f4b31
Create Date: 2026-10-26 03:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b9e1a2c3d45"
down_revision: str | Sequence[str] | None = "6a8d0c2f4b31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO users "
            "(id, email, password_hash, full_name, role_id, status, created_at, updated_at) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000001', 'student@example.com', "
            "'read-only-seed', 'Demo Student', "
            "(SELECT id FROM roles WHERE code = 'STUDENT'), 'ACTIVE', DEFAULT, DEFAULT), "
            "('00000000-0000-0000-0000-000000000003', 'teacher@example.com', "
            "'read-only-seed', 'Demo Teacher', "
            "(SELECT id FROM roles WHERE code = 'TEACHER'), 'ACTIVE', DEFAULT, DEFAULT) "
            "ON CONFLICT DO NOTHING"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO students "
            "(id, user_id, education_level, learning_goal, timezone, status, "
            "created_at, updated_at) "
            "VALUES "
            "('00000000-0000-0000-0000-000000000002', "
            "'00000000-0000-0000-0000-000000000001', 'university', "
            "'Improve mathematics', 'Europe/Minsk', 'ACTIVE', DEFAULT, DEFAULT) "
            "ON CONFLICT DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM users WHERE id IN "
            "('00000000-0000-0000-0000-000000000001', "
            "'00000000-0000-0000-0000-000000000003')"
        )
    )
