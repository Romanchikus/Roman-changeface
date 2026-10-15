from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.types import TypeDecorator


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
