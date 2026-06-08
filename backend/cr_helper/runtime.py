"""Process-local productionization primitives: rate limiter, metrics, TTL cache.

In-memory and thread-safe (FastAPI runs sync handlers in a threadpool). For the
multi-process/full stack these move to Redis behind the same surfaces.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict

from .config import settings


class RateLimiter:
    """Per-key token bucket. capacity = requests/min, refilled continuously."""

    def __init__(self, per_min: int):
        self.capacity = float(per_min)
        self.refill = per_min / 60.0
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.capacity <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True


class Metrics:
    def __init__(self):
        self.start = time.time()
        self.requests = 0
        self.errors = 0
        self.rate_limited = 0
        self.by_path: dict[str, int] = {}
        self._lock = threading.Lock()

    def record(self, path: str, status: int) -> None:
        with self._lock:
            self.requests += 1
            self.by_path[path] = self.by_path.get(path, 0) + 1
            if status >= 500:
                self.errors += 1

    def snapshot(self) -> dict:
        top = dict(sorted(self.by_path.items(), key=lambda kv: -kv[1])[:8])
        return {
            "uptime_s": round(time.time() - self.start, 1),
            "requests": self.requests,
            "errors": self.errors,
            "rate_limited": self.rate_limited,
            "top_paths": top,
        }


class TTLCache:
    def __init__(self, ttl: float, maxsize: int = 256):
        self.ttl = ttl
        self.maxsize = maxsize
        self._data: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def get(self, key: str):
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry and now - entry[0] < self.ttl:
                self.hits += 1
                self._data.move_to_end(key)
                return entry[1]
            if entry:
                del self._data[key]
            self.misses += 1
            return None

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = (time.time(), value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def stats(self) -> dict:
        return {"size": len(self._data), "hits": self.hits, "misses": self.misses}


limiter = RateLimiter(settings.rate_limit_per_min)
metrics = Metrics()
analysis_cache = TTLCache(settings.cache_ttl_seconds)
