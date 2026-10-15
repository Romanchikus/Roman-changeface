"""extra source faces and their target order"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("input_image_2_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("input_image_3_id", sa.Integer(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("face_order", sa.String(length=32), nullable=False, server_default="left-right"),
    )
    op.create_foreign_key("fk_jobs_input_image_2_id", "jobs", "media", ["input_image_2_id"], ["id"])
    op.create_foreign_key("fk_jobs_input_image_3_id", "jobs", "media", ["input_image_3_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_input_image_3_id", "jobs", type_="foreignkey")
    op.drop_constraint("fk_jobs_input_image_2_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "face_order")
    op.drop_column("jobs", "input_image_3_id")
    op.drop_column("jobs", "input_image_2_id")
