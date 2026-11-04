from __future__ import annotations

import time
from collections import defaultdict, deque


class DevelopmentRateLimiter:
    """Process-local limiter for development/small single-worker deployments."""

    def __init__(self, requests: int = 30, window_seconds: int = 60) -> None:
        self.requests = requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        events = self._events[key]
        while events and events[0] <= current - self.window_seconds:
            events.popleft()
        if len(events) >= self.requests:
            return False
        events.append(current)
        return True
