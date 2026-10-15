import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.metrics.cache import cache
from app.metrics.loop import persist, run
from app.metrics.middleware import TrafficMiddleware
from app.shared.config import get_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    stop = asyncio.Event()
    task = asyncio.create_task(run(stop))
    try:
        yield
    finally:
        stop.set()
        await task
        await persist()
        await cache.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Changeface", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrafficMiddleware)
    app.include_router(router)
    return app


app = create_app()
