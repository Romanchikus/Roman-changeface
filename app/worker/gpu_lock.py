import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager

import redis

from app.shared.config import get_settings
from app.shared.errors import GpuBusy

LOCK_KEY = "changeface:gpu"
_RELEASE = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""


@contextmanager
def gpu_slot() -> Generator[None, None, None]:
    settings = get_settings()
    if settings.inference_backend != "hyperswap":
        yield
        return
    if not settings.redis_url:
        raise GpuBusy("Redis is required to serialize GPU jobs.")

    client = redis.Redis.from_url(settings.redis_url)
    token = str(uuid.uuid4())
    deadline = time.monotonic() + settings.gpu_lock_wait_sec
    held = False
    while time.monotonic() < deadline:
        if client.set(LOCK_KEY, token, nx=True, ex=settings.gpu_lock_ttl_sec):
            held = True
            break
        time.sleep(0.2)
    if not held:
        raise GpuBusy("GPU is busy with another job.")
    try:
        yield
    finally:
        client.eval(_RELEASE, 1, LOCK_KEY, token)
