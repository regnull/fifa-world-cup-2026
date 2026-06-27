import responses as resp
from scrape.elo import fetch_elo

SAMPLE_HTML = """
<html><body>
<table>
<tr><th>Rank</th><th>Team</th><th>Rating</th></tr>
<tr><td>1</td><td>Brazil</td><td>2145</td></tr>
<tr><td>2</td><td>France</td><td>2101</td></tr>
<tr><td>3</td><td>Argentina</td><td>2088</td></tr>
</table>
</body></html>
"""

@resp.activate
def test_fetch_elo_parses_ratings():
    resp.add(resp.GET, "https://www.eloratings.net/World", body=SAMPLE_HTML, status=200)
    result = fetch_elo(use_cache=False)
    assert result["Brazil"] == 2145.0
    assert result["France"] == 2101.0
    assert result["Argentina"] == 2088.0

@resp.activate
def test_fetch_elo_normalizes_names():
    html = SAMPLE_HTML.replace("Brazil", "brazil")
    resp.add(resp.GET, "https://www.eloratings.net/World", body=html, status=200)
    result = fetch_elo(use_cache=False)
    assert "Brazil" in result

def test_fetch_elo_returns_dict():
    # This test uses the cache to avoid network calls in CI
    # Seed a fake cache entry
    from scrape.cache import cache_set
    cache_set("elo_world", SAMPLE_HTML)
    result = fetch_elo(use_cache=True)
    assert isinstance(result, dict)
    assert len(result) > 0
