# Rules

- No `git commit`, `git push`, or history rewrite.
- Simple names. Split large logic. No extra abstractions.
- Do not add a function for one, two, or three simple actions. Write them where the work happens.
- Short docstrings only for public or non-obvious methods.
- Log operations and failures. Never log secrets, tokens, passwords, or cookies.
- Test behavior when it can be tested, including failure, auth, and rollback.
- DB tests hit real PostgreSQL. Do not mock those queries.
- Avoid use dicts, use typed objects instead.

- Async FastAPI and async SQLAlchemy. `select()` only, not legacy `Query`.
- Thin routers. Use cases in services. SQL in `app/db/` query modules. Schemas in `app/schemas.py`, not on models.
- New HTTP area: `app/api/routers/<area>.py`.
- Commit at the request or use-case boundary. Query helpers do not commit.
- No open transaction during CPU, external calls, or other I/O.
- `asyncio.gather` for independent I/O only. Never share a DB session. Bound large fan-out.
- Auth and authorization are separate. Load the user, or the user plus related rows in one query.
- No nullable column unless absence is stored. Index real query patterns. Alembic for schema changes. Do not edit an applied revision.
- List filters are `fastapi-filter` models (`FilterDepends`). Do not declare each filter as its own endpoint argument.
- External calls go through a client or `Protocol`, with an explicit timeout. No blocking libraries on the request path.
- `dataclass(slots=True)` for internal records. NumPy/Pandas for large numeric work.
- Stream or generate data that is not needed now. Pickle only trusted internal data.

- Routers `app/api/routers/`. Auth `app/api/deps.py`. Models `app/db/models.py`. Session `app/db/session.py`. Worker `app/worker/`. Inference `app/inference/`. Settings `app/shared/`. Migrations `migrations/`. UI `frontend/`.
- `facefusion/` is a separate checkout. Call it from `app/inference/`.
- Music is a module of this app: `app/services/music.py` and `app/inference/acestep.py`. It stores files the same way a face swap does. The worker currently passes.
- Skip a layer this service does not need.
