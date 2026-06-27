import pytest
import scrape.cache as _cache_module


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Redirect cache I/O to a temp directory so tests never touch the real cache."""
    monkeypatch.setattr(_cache_module, "_CACHE_DIR", str(tmp_path))
