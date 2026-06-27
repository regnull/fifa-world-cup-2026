import json
import requests
from scrape.models import MatchOdds
from scrape.names import normalize
from scrape.cache import cache_get, cache_set

_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}


def fetch_odds(use_cache: bool = True) -> dict[tuple[str, str], MatchOdds]:
    """Parse 1X2 odds from ESPN scoreboard. Returns empty dict on any failure."""
    try:
        raw = cache_get("schedule") if use_cache else None
        if raw is None:
            r = requests.get(_URL, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            raw = r.text
            cache_set("schedule", raw)
        return _parse(raw)
    except Exception:
        return {}


def _parse(raw: str) -> dict[tuple[str, str], MatchOdds]:
    data = json.loads(raw)
    result: dict[tuple[str, str], MatchOdds] = {}
    for event in data.get("events", []):
        for comp in event.get("competitions", []):
            odds_list = comp.get("odds", [])
            if not odds_list:
                continue
            odds_data = odds_list[0].get("moneyline", {})
            if not odds_data:
                continue
            try:
                home_ml = odds_data["home"]["close"]["odds"]
                away_ml = odds_data["away"]["close"]["odds"]
                draw_ml = odds_data["draw"]["close"]["odds"]
            except KeyError:
                continue
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = away = ""
            for c in competitors:
                name = normalize(c["team"]["displayName"])
                if c.get("homeAway") == "home":
                    home = name
                else:
                    away = name
            if not home or not away:
                continue
            try:
                oh = _american_to_decimal(home_ml)
                od = _american_to_decimal(draw_ml)
                oa = _american_to_decimal(away_ml)
                result[(home, away)] = MatchOdds(
                    home=home, away=away,
                    odds_home=oh, odds_draw=od, odds_away=oa,
                )
            except (ValueError, TypeError):
                continue
    return result


def _american_to_decimal(ml: str) -> float:
    """Convert American moneyline string (e.g. '-110', '+425') to decimal odds."""
    val = int(ml)
    if val > 0:
        return val / 100.0 + 1.0
    else:
        return 100.0 / abs(val) + 1.0


def _parse_odds_row(
    match_text: str, o1: str, ox: str, o2: str
) -> tuple[str, str, float, float, float]:
    """Parse a 'Home - Away' text and three decimal odds strings. Used in tests."""
    parts = match_text.split(" - ", 1)
    home = normalize(parts[0].strip())
    away = normalize(parts[1].strip())
    return home, away, float(o1), float(ox), float(o2)
