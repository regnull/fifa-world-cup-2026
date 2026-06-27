import responses as resp
from scrape.elo import fetch_elo
from scrape.cache import cache_set

SAMPLE_TSV = "\n".join([
    "1\t1\tBR\t2145\t1\t2200",
    "2\t2\tFR\t2101\t1\t2150",
    "3\t3\tAR\t2088\t1\t2140",
])

_URL = "https://www.eloratings.net/World.tsv"


@resp.activate
def test_fetch_elo_parses_ratings():
    resp.add(resp.GET, _URL, body=SAMPLE_TSV, status=200)
    result = fetch_elo(use_cache=False)
    assert result["Brazil"] == 2145.0
    assert result["France"] == 2101.0
    assert result["Argentina"] == 2088.0


@resp.activate
def test_fetch_elo_maps_codes_to_canonical_names():
    resp.add(resp.GET, _URL, body=SAMPLE_TSV, status=200)
    result = fetch_elo(use_cache=False)
    assert "Brazil" in result
    assert "France" in result
    assert "Argentina" in result


def test_fetch_elo_returns_dict_from_cache():
    cache_set("elo_world", SAMPLE_TSV)
    result = fetch_elo(use_cache=True)
    assert isinstance(result, dict)
    assert len(result) >= 3
