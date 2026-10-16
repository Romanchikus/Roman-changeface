"""text jobs store Llama parameters as JSON"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.types import AwareDateTime

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "text_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", AwareDateTime(), nullable=False),
        sa.Column("started_at", AwareDateTime(), nullable=True),
        sa.Column("finished_at", AwareDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_text_jobs_status", "text_jobs", ["status"])
    op.create_index("ix_text_jobs_created_at", "text_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_text_jobs_created_at", table_name="text_jobs")
    op.drop_index("ix_text_jobs_status", table_name="text_jobs")
    op.drop_table("text_jobs")
