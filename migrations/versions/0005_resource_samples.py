"""resource samples for cpu, vram, and gpu history"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.types import AwareDateTime

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resource_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sampled_at", AwareDateTime(), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("ram_used_bytes", sa.BigInteger(), nullable=False),
        sa.Column("ram_total_bytes", sa.BigInteger(), nullable=False),
        sa.Column("vram_used_bytes", sa.BigInteger(), nullable=True),
        sa.Column("vram_total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("gpu_util_percent", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sampled_at"),
    )
    op.create_index("ix_resource_samples_sampled_at", "resource_samples", ["sampled_at"])


def downgrade() -> None:
    op.drop_index("ix_resource_samples_sampled_at", table_name="resource_samples")
    op.drop_table("resource_samples")
