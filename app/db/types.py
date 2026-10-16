import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.types import TypeDecorator


@dataclass(slots=True)
class MediaSnapshot:
    id: int
    path: str
    filename: str
    order: int
    role: str


@dataclass(slots=True)
class MusicParameters:
    task_type: str
    caption: str
    duration_sec: float
    seed: int
    audio_id: int | None


class MediaSnapshotList(TypeDecorator):
    """JSON list of media snapshots. Python values stay `MediaSnapshot` objects."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: list[MediaSnapshot] | None, dialect):  # type: ignore[no-untyped-def]
        if not value:
            return []
        return [
            {
                "id": item.id,
                "path": item.path,
                "filename": item.filename,
                "order": item.order,
                "role": item.role,
            }
            for item in value
        ]

    def process_result_value(self, value, dialect) -> list[MediaSnapshot]:  # type: ignore[no-untyped-def]
        if not value:
            return []
        rows = json.loads(value) if isinstance(value, str) else value
        return [
            MediaSnapshot(
                id=int(row["id"]),
                path=str(row["path"]),
                filename=str(row["filename"]),
                order=int(row["order"]),
                role=str(row["role"]),
            )
            for row in rows
        ]


class MusicParametersColumn(TypeDecorator):
    """JSON object stored as text. Python values stay `MusicParameters`."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: MusicParameters | None, dialect) -> str:  # type: ignore[no-untyped-def]
        if value is None:
            return "{}"
        return json.dumps(
            {
                "task_type": value.task_type,
                "caption": value.caption,
                "duration_sec": value.duration_sec,
                "seed": value.seed,
                "audio_id": value.audio_id,
            }
        )

    def process_result_value(self, value, dialect) -> MusicParameters:  # type: ignore[no-untyped-def]
        raw = json.loads(value or "{}")
        audio_id = raw.get("audio_id")
        return MusicParameters(
            task_type=str(raw.get("task_type", "")),
            caption=str(raw.get("caption", "")),
            duration_sec=float(raw.get("duration_sec", 0)),
            seed=int(raw.get("seed", -1)),
            audio_id=None if audio_id is None else int(audio_id),
        )


@dataclass(slots=True)
class TextParameters:
    model: str
    prompt: str
    max_new_tokens: int
    system: str | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    typical_p: float | None = None
    do_sample: bool | None = None
    seed: int | None = None
    repetition_penalty: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    stop: list[str] | None = None
    ignore_eos: bool | None = None
    min_new_tokens: int | None = None


class TextParametersColumn(TypeDecorator):
    """JSON object of Llama sampling settings. Python values stay `TextParameters`."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: TextParameters | None, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return {}
        payload: dict[str, object] = {
            "model": value.model,
            "prompt": value.prompt,
            "max_new_tokens": value.max_new_tokens,
        }
        optional: tuple[tuple[str, object], ...] = (
            ("system", value.system),
            ("temperature", value.temperature),
            ("top_p", value.top_p),
            ("top_k", value.top_k),
            ("min_p", value.min_p),
            ("typical_p", value.typical_p),
            ("do_sample", value.do_sample),
            ("seed", value.seed),
            ("repetition_penalty", value.repetition_penalty),
            ("presence_penalty", value.presence_penalty),
            ("frequency_penalty", value.frequency_penalty),
            ("stop", value.stop),
            ("ignore_eos", value.ignore_eos),
            ("min_new_tokens", value.min_new_tokens),
        )
        for key, item in optional:
            if item is not None:
                payload[key] = item
        return payload

    def process_result_value(self, value, dialect) -> TextParameters:  # type: ignore[no-untyped-def]
        raw = json.loads(value) if isinstance(value, str) else (value or {})
        stop = raw.get("stop")
        return TextParameters(
            model=str(raw["model"]),
            prompt=str(raw["prompt"]),
            max_new_tokens=int(raw["max_new_tokens"]),
            system=None if raw.get("system") is None else str(raw["system"]),
            temperature=None if raw.get("temperature") is None else float(raw["temperature"]),
            top_p=None if raw.get("top_p") is None else float(raw["top_p"]),
            top_k=None if raw.get("top_k") is None else int(raw["top_k"]),
            min_p=None if raw.get("min_p") is None else float(raw["min_p"]),
            typical_p=None if raw.get("typical_p") is None else float(raw["typical_p"]),
            do_sample=None if raw.get("do_sample") is None else bool(raw["do_sample"]),
            seed=None if raw.get("seed") is None else int(raw["seed"]),
            repetition_penalty=None if raw.get("repetition_penalty") is None else float(raw["repetition_penalty"]),
            presence_penalty=None if raw.get("presence_penalty") is None else float(raw["presence_penalty"]),
            frequency_penalty=None if raw.get("frequency_penalty") is None else float(raw["frequency_penalty"]),
            stop=None if stop is None else [str(item) for item in stop],
            ignore_eos=None if raw.get("ignore_eos") is None else bool(raw["ignore_eos"]),
            min_new_tokens=None if raw.get("min_new_tokens") is None else int(raw["min_new_tokens"]),
        )


class AwareDateTime(TypeDecorator):
    """Timezone-aware timestamp.

    PostgreSQL stores it as TIMESTAMP WITH TIME ZONE. Other engines store an
    ISO-8601 string that includes the offset, so the timezone survives a round trip.
    """

    impl = String(40)
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TIMESTAMP(timezone=True))
        return dialect.type_descriptor(String(40))

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | str | None:  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("datetime must be timezone-aware")
        if dialect.name == "postgresql":
            return value
        return value.isoformat()

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
            raise ValueError("stored datetime is missing a timezone")
        return parsed
