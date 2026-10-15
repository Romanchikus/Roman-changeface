"""widen resource sample byte counters past 2 GiB"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("ram_used_bytes", "ram_total_bytes", "vram_used_bytes", "vram_total_bytes")


def upgrade() -> None:
    for name in _COLUMNS:
        op.alter_column("resource_samples", name, type_=sa.BigInteger(), existing_type=sa.Integer())


def downgrade() -> None:
    for name in reversed(_COLUMNS):
        op.alter_column("resource_samples", name, type_=sa.Integer(), existing_type=sa.BigInteger())
