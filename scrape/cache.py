import os

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


def cache_get(key: str) -> str | None:
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def cache_set(key: str, value: str) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        f.write(value)


def _cache_path(key: str) -> str:
    safe = key.replace("/", "_").replace(":", "_")
    return os.path.join(_CACHE_DIR, safe + ".txt")
