from datetime import datetime, timezone

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import (
    AwareDateTime,
    MediaSnapshot,
    MediaSnapshotList,
    MusicParameters,
    MusicParametersColumn,
    TextParameters,
    TextParametersColumn,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    filename: Mapped[str] = mapped_column(String(200), index=True)
    path: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(64))
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), default=utcnow, index=True
    )
    thumbnail: Mapped["Thumbnail | None"] = relationship(
        back_populates="media", uselist=False
    )


class Thumbnail(Base):
    __tablename__ = "thumbnails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), unique=True)
    path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), default=utcnow, index=True
    )
    media: Mapped[Media] = relationship(back_populates="thumbnail")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), default=utcnow, index=True
    )
    last_activity_at: Mapped[datetime] = mapped_column(AwareDateTime(), default=utcnow)
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user")


class AuthSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(AwareDateTime(), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(AwareDateTime(), index=True)
    user: Mapped[User] = relationship(back_populates="sessions")


class ResourceSample(Base):
    __tablename__ = "resource_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sampled_at: Mapped[datetime] = mapped_column(AwareDateTime(), unique=True, index=True)
    cpu_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_used_bytes: Mapped[int] = mapped_column(BigInteger)
    ram_total_bytes: Mapped[int] = mapped_column(BigInteger)
    vram_used_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    vram_total_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    gpu_util_percent: Mapped[float | None] = mapped_column(Float, nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    media_ids: Mapped[list[MediaSnapshot]] = mapped_column(MediaSnapshotList, nullable=False, default=list)
    face_order: Mapped[str] = mapped_column(String(32), default="left-right")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inference_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    simulated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), default=utcnow, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)


class MusicJob(Base):
    __tablename__ = "music_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    task_type: Mapped[str] = mapped_column(String(32), default="")
    seed: Mapped[int] = mapped_column(Integer, default=-1)
    inference_steps: Mapped[int] = mapped_column(Integer, default=8)
    shift: Mapped[float] = mapped_column(Float, default=3.0)
    parameters: Mapped[MusicParameters] = mapped_column(MusicParametersColumn, nullable=False)
    media_ids: Mapped[list[MediaSnapshot]] = mapped_column(MediaSnapshotList, nullable=False, default=list)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), default=utcnow, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)


class TextJob(Base):
    __tablename__ = "text_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[TextParameters] = mapped_column(TextParametersColumn, nullable=False)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime(), default=utcnow, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(AwareDateTime(), nullable=True)
