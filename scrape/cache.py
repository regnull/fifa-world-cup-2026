import os
import time

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")

# Default freshness window for live, time-sensitive tournament data (schedule,
# standings, odds, bracket). During a running tournament these change daily, so
# anything older than this is treated as a cache miss and re-scraped.
LIVE_TTL = 3 * 3600  # 3 hours


def cache_get(key: str, max_age: float | None = None) -> str | None:
    """Return the cached value for ``key``, or ``None`` on a miss.

    If ``max_age`` (seconds) is given, an entry older than that is treated as a
    miss so stale live data gets re-scraped instead of being served forever.
    """
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    if max_age is not None and (time.time() - os.path.getmtime(path)) > max_age:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def cache_set(key: str, value: str) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        f.write(value)


def _cache_path(key: str) -> str:
    safe = key.replace("/", "_").replace(":", "_")
    return os.path.join(_CACHE_DIR, safe + ".txt")
