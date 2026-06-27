import requests
from bs4 import BeautifulSoup
from scrape.names import normalize
from scrape.cache import cache_get, cache_set

_URL = "https://www.eloratings.net/World"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_elo(use_cache: bool = True) -> dict[str, float]:
    """Return dict of canonical team name → Elo rating."""
    raw = cache_get("elo_world") if use_cache else None
    if raw is None:
        r = requests.get(_URL, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        raw = r.text
        cache_set("elo_world", raw)

    return _parse(raw)


def _parse(html: str) -> dict[str, float]:
    soup = BeautifulSoup(html, "lxml")
    result: dict[str, float] = {}
    for row in soup.select("table tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        try:
            team = normalize(cells[1].get_text(strip=True))
            rating = float(cells[2].get_text(strip=True).replace(",", ""))
            result[team] = rating
        except (ValueError, IndexError):
            continue
    return result
