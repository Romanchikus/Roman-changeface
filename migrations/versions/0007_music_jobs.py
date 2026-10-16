"""music jobs, and one JSON list of media on each swap"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.db.types import AwareDateTime

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MEDIA_COLUMNS = (
    "input_image_id",
    "input_image_2_id",
    "input_image_3_id",
    "input_video_id",
    "output_video_id",
)


def _entry(bind, media_id: int, order: int, role: str) -> dict[str, object]:
    media = bind.execute(
        sa.text("SELECT path, filename FROM media WHERE id = :id"),
        {"id": media_id},
    ).mappings().one()
    return {
        "id": media_id,
        "path": media["path"],
        "filename": media["filename"],
        "order": order,
        "role": role,
    }


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("media_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, input_image_id, input_image_2_id, input_image_3_id, "
            "input_video_id, output_video_id FROM jobs"
        )
    ).mappings()
    for row in rows:
        entries: list[dict[str, object]] = []
        for order, column in enumerate(("input_image_id", "input_image_2_id", "input_image_3_id")):
            media_id = row[column]
            if media_id is None:
                continue
            entries.append(_entry(bind, media_id, order, "source"))
        entries.append(_entry(bind, row["input_video_id"], 0, "video"))
        entries.append(_entry(bind, row["output_video_id"], 0, "output"))
        bind.execute(
            sa.text("UPDATE jobs SET media_ids = CAST(:payload AS JSON) WHERE id = :id"),
            {"payload": json.dumps(entries), "id": row["id"]},
        )

    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys("jobs"):
        if set(fk["constrained_columns"]) & set(_MEDIA_COLUMNS) and fk["name"]:
            op.drop_constraint(fk["name"], "jobs", type_="foreignkey")
    for index in inspector.get_indexes("jobs"):
        if set(index["column_names"]) & set(_MEDIA_COLUMNS):
            op.drop_index(index["name"], table_name="jobs")
    for column in _MEDIA_COLUMNS:
        op.drop_column("jobs", column)

    op.create_table(
        "music_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=32), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("inference_steps", sa.Integer(), nullable=False),
        sa.Column("shift", sa.Float(), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),
        sa.Column("media_ids", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", AwareDateTime(), nullable=False),
        sa.Column("started_at", AwareDateTime(), nullable=True),
        sa.Column("finished_at", AwareDateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_music_jobs_status", "music_jobs", ["status"])
    op.create_index("ix_music_jobs_created_at", "music_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_music_jobs_created_at", table_name="music_jobs")
    op.drop_index("ix_music_jobs_status", table_name="music_jobs")
    op.drop_table("music_jobs")

    op.add_column("jobs", sa.Column("input_image_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("input_image_2_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("input_image_3_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("input_video_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("output_video_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, media_ids FROM jobs")).mappings()
    for row in rows:
        raw = row["media_ids"]
        entries = raw if isinstance(raw, list) else json.loads(raw or "[]")
        values = {
            "source": [],
            "video": None,
            "output": None,
        }
        for entry in sorted(entries, key=lambda item: int(item["order"])):
            if entry["role"] == "source":
                values["source"].append(entry["id"])
            elif entry["role"] == "video":
                values["video"] = entry["id"]
            elif entry["role"] == "output":
                values["output"] = entry["id"]
        faces = values["source"] + [None, None, None]
        bind.execute(
            sa.text(
                "UPDATE jobs SET input_image_id = :image, input_image_2_id = :image_2, "
                "input_image_3_id = :image_3, input_video_id = :video, output_video_id = :output "
                "WHERE id = :id"
            ),
            {
                "image": faces[0],
                "image_2": faces[1],
                "image_3": faces[2],
                "video": values["video"],
                "output": values["output"],
                "id": row["id"],
            },
        )
    op.alter_column("jobs", "input_image_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("jobs", "input_video_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("jobs", "output_video_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("jobs_input_image_id_fkey", "jobs", "media", ["input_image_id"], ["id"])
    op.create_foreign_key("fk_jobs_input_image_2_id", "jobs", "media", ["input_image_2_id"], ["id"])
    op.create_foreign_key("fk_jobs_input_image_3_id", "jobs", "media", ["input_image_3_id"], ["id"])
    op.create_foreign_key("jobs_input_video_id_fkey", "jobs", "media", ["input_video_id"], ["id"])
    op.create_foreign_key("jobs_output_video_id_fkey", "jobs", "media", ["output_video_id"], ["id"])
    op.create_index("ix_jobs_input_image_id", "jobs", ["input_image_id"])
    op.create_index("ix_jobs_input_video_id", "jobs", ["input_video_id"])
    op.create_index("ix_jobs_output_video_id", "jobs", ["output_video_id"])
    op.drop_column("jobs", "media_ids")
