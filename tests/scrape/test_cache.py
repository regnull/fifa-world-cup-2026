import os
import time

from scrape.cache import cache_get, cache_set, _cache_path


def test_fresh_entry_is_returned():
    cache_set("k", "value")
    assert cache_get("k") == "value"


def test_fresh_entry_within_max_age_is_returned():
    cache_set("k", "value")
    assert cache_get("k", max_age=3600) == "value"


def test_stale_entry_beyond_max_age_is_a_miss():
    cache_set("k", "value")
    # Backdate the file mtime so it is older than max_age.
    path = _cache_path("k")
    old = time.time() - 7200
    os.utime(path, (old, old))
    assert cache_get("k", max_age=3600) is None


def test_no_max_age_never_expires():
    cache_set("k", "value")
    path = _cache_path("k")
    old = time.time() - 10_000_000
    os.utime(path, (old, old))
    assert cache_get("k") == "value"
