import time
from collections import deque


class Traffic:
    def __init__(self) -> None:
        self.inflight = 0
        self._hits: deque[float] = deque()

    def enter(self) -> None:
        self.inflight += 1
        now = time.monotonic()
        self._hits.append(now)
        self._drop_old(now)

    def leave(self) -> None:
        self.inflight = max(0, self.inflight - 1)

    def recent(self, window_sec: float = 10) -> int:
        now = time.monotonic()
        self._drop_old(now, window_sec)
        return len(self._hits)

    def idle(self, window_sec: float = 10) -> bool:
        return self.inflight == 0 and self.recent(window_sec) == 0

    def _drop_old(self, now: float, window_sec: float = 10) -> None:
        cutoff = now - window_sec
        while self._hits and self._hits[0] < cutoff:
            self._hits.popleft()


traffic = Traffic()
