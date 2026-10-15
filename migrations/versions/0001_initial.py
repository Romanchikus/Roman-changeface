"""initial schema"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.types import AwareDateTime

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=200), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("created_at", AwareDateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_kind", "media", ["kind"])
    op.create_index("ix_media_filename", "media", ["filename"])
    op.create_index("ix_media_created_at", "media", ["created_at"])

    op.create_table(
        "thumbnails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("media_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("created_at", AwareDateTime(), nullable=False),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_id"),
    )
    op.create_index("ix_thumbnails_created_at", "thumbnails", ["created_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_image_id", sa.Integer(), nullable=False),
        sa.Column("input_video_id", sa.Integer(), nullable=False),
        sa.Column("output_video_id", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=64), nullable=True),
        sa.Column("detector_name", sa.String(length=64), nullable=True),
        sa.Column("inference_ms", sa.Integer(), nullable=True),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.Column("created_at", AwareDateTime(), nullable=False),
        sa.Column("started_at", AwareDateTime(), nullable=True),
        sa.Column("finished_at", AwareDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["input_image_id"], ["media.id"]),
        sa.ForeignKeyConstraint(["input_video_id"], ["media.id"]),
        sa.ForeignKeyConstraint(["output_video_id"], ["media.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_input_image_id", "jobs", ["input_image_id"])
    op.create_index("ix_jobs_input_video_id", "jobs", ["input_video_id"])
    op.create_index("ix_jobs_output_video_id", "jobs", ["output_video_id"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_created_at", table_name="jobs")
    op.drop_index("ix_jobs_output_video_id", table_name="jobs")
    op.drop_index("ix_jobs_input_video_id", table_name="jobs")
    op.drop_index("ix_jobs_input_image_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_thumbnails_created_at", table_name="thumbnails")
    op.drop_table("thumbnails")
    op.drop_index("ix_media_created_at", table_name="media")
    op.drop_index("ix_media_filename", table_name="media")
    op.drop_index("ix_media_kind", table_name="media")
    op.drop_table("media")
