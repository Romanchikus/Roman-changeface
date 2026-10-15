# db

Async session in `session.py`. Tables in `models.py`. SQL in the query modules. `select()` only. List queries take a `fastapi-filter` and call `filter()` then `sort()`. No commit here unless the function owns the transaction. No transaction across inference or file I/O. No `asyncio.gather` on one session. Join related rows. New Alembic revision for schema changes.
