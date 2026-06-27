import re
import requests
from bs4 import BeautifulSoup
from scrape.models import MatchOdds
from scrape.names import normalize
from scrape.cache import cache_get, cache_set

_URL = "https://www.betexplorer.com/football/world/fifa-world-cup/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.betexplorer.com/",
}


def fetch_odds(use_cache: bool = True) -> dict[tuple[str, str], MatchOdds]:
    """Scrape 1X2 odds. Returns empty dict on any failure."""
    try:
        raw = cache_get("odds") if use_cache else None
        if raw is None:
            r = requests.get(_URL, headers=_HEADERS, timeout=20)
            r.raise_for_status()
            raw = r.text
            cache_set("odds", raw)
        return _parse(raw)
    except Exception:
        return {}


def _parse(html: str) -> dict[tuple[str, str], MatchOdds]:
    soup = BeautifulSoup(html, "lxml")
    result: dict[tuple[str, str], MatchOdds] = {}
    for row in soup.select("table.table-main tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        match_text = cells[0].get_text(strip=True)
        if " - " not in match_text:
            continue
        odds_cells = [c.get_text(strip=True) for c in cells[1:4]]
        try:
            home, away, oh, od, oa = _parse_odds_row(match_text, *odds_cells)
            key = (home, away)
            result[key] = MatchOdds(home=home, away=away,
                                     odds_home=oh, odds_draw=od, odds_away=oa)
        except (ValueError, TypeError):
            continue
    return result


def _parse_odds_row(
    match_text: str, o1: str, ox: str, o2: str
) -> tuple[str, str, float, float, float]:
    parts = match_text.split(" - ", 1)
    home = normalize(parts[0].strip())
    away = normalize(parts[1].strip())
    return home, away, float(o1), float(ox), float(o2)
