from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import String, cast, or_
from sqlalchemy.sql import Select

from app.db.models import Job, Media

PAGE_LIMIT = 100


class JobFilter(Filter):
    q: str | None = None
    id: int | None = None
    status: str | None = None
    model_name: str | None = None
    face_order: str | None = None
    order_by: list[str] | None = ["-created_at"]

    class Constants(Filter.Constants):
        model = Job
        search_field_name = "q"
        search_model_fields = ["status", "model_name", "face_order"]

    def filter(self, query: Select) -> Select:
        """Apply exact fields, then the `q` search across the job and its file names."""
        query = Filter.filter(self.model_copy(update={"q": None}), query)
        if not self.q:
            return query
        like = f"%{self.q}%"
        clauses = [
            Job.status.ilike(like),
            Job.model_name.ilike(like),
            Job.face_order.ilike(like),
            cast(Job.media_ids, String).ilike(like),
        ]
        if self.q.isdigit():
            clauses.append(Job.id == int(self.q))
        return query.where(or_(*clauses))


class MediaFilter(Filter):
    q: str | None = None
    id: int | None = None
    filename: str | None = None
    content_type: str | None = None
    order_by: list[str] | None = ["-created_at"]

    class Constants(Filter.Constants):
        model = Media
        search_field_name = "q"
        search_model_fields = ["filename", "content_type"]
