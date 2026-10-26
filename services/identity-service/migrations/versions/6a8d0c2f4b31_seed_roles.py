"""seed roles

Revision ID: 6a8d0c2f4b31
Revises: ee750caf4e92
Create Date: 2026-10-26 02:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "6a8d0c2f4b31"
down_revision: str | Sequence[str] | None = "ee750caf4e92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO roles (id, code, name) VALUES "
            "(1, 'STUDENT', 'Ученик'), "
            "(2, 'TEACHER', 'Преподаватель'), "
            "(3, 'ADMIN', 'Администратор') "
            "ON CONFLICT (code) DO NOTHING"
        )
    )
    op.execute(sa.text("SELECT setval('roles_id_seq', 3, true)"))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM roles WHERE code IN ('STUDENT', 'TEACHER', 'ADMIN')"))
