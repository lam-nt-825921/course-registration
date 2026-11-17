"""audit_logs: cho phép student_id / course_class_id NULL (LOGIN, LOGOUT, RATE_LIMIT_EXCEEDED)

Revision ID: a3f1c9d2b7e4
Revises: 3768f0350384
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3f1c9d2b7e4"
down_revision: Union[str, Sequence[str], None] = "3768f0350384"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("audit_logs", "student_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.alter_column("audit_logs", "course_class_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM audit_logs WHERE student_id IS NULL OR course_class_id IS NULL")
    op.alter_column("audit_logs", "course_class_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("audit_logs", "student_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
