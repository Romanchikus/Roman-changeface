from datetime import datetime, timezone

from sqlalchemy import BigInteger, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import AwareDateTime


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
    input_image_id: Mapped[int] = mapped_column(ForeignKey("media.id"), index=True)
    input_image_2_id: Mapped[int | None] = mapped_column(
        ForeignKey("media.id"), nullable=True
    )
    input_image_3_id: Mapped[int | None] = mapped_column(
        ForeignKey("media.id"), nullable=True
    )
    input_video_id: Mapped[int] = mapped_column(ForeignKey("media.id"), index=True)
    output_video_id: Mapped[int] = mapped_column(ForeignKey("media.id"), index=True)
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
    input_image: Mapped[Media] = relationship(foreign_keys=[input_image_id])
    input_image_2: Mapped[Media | None] = relationship(foreign_keys=[input_image_2_id])
    input_image_3: Mapped[Media | None] = relationship(foreign_keys=[input_image_3_id])
    input_video: Mapped[Media] = relationship(foreign_keys=[input_video_id])
    output_video: Mapped[Media] = relationship(foreign_keys=[output_video_id])
