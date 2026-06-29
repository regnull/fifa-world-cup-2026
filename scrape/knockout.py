import json
import requests
from scrape.models import KnockoutResult
from scrape.names import normalize
from scrape.cache import cache_get, cache_set, LIVE_TTL

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
_DATES = ["20260628", "20260629", "20260630", "20260701", "20260702", "20260703",
          "20260704", "20260705", "20260706", "20260707", "20260708", "20260709",
          "20260710", "20260711", "20260712", "20260713", "20260714", "20260715",
          "20260716", "20260717", "20260718", "20260719"]
_KNOCKOUT_MARKERS = ("Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final")


def fetch_knockout_results(use_cache: bool = True) -> dict[frozenset, KnockoutResult]:
    """Return completed knockout games keyed by frozenset({home, away}).

    The key is orientation-independent so a bracket matchup can be looked up
    regardless of which team it lists as home. Returns {} on any failure.
    """
    try:
        raw = cache_get("knockout_results", max_age=LIVE_TTL) if use_cache else None
        if raw is None:
            games = _scrape()
            raw = json.dumps(games)
            if use_cache:
                cache_set("knockout_results", raw)
        return {
            frozenset({g["home"], g["away"]}): KnockoutResult(**g)
            for g in json.loads(raw)
        }
    except Exception:
        return {}


def _scrape() -> list[dict]:
    games: dict[frozenset, dict] = {}
    for date in _DATES:
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
            f"?dates={date}"
        )
        try:
            r = requests.get(url, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            continue
        for g in _parse(data):
            games[frozenset({g["home"], g["away"]})] = g
    return list(games.values())


def _parse(data: dict) -> list[dict]:
    out: list[dict] = []
    for event in data.get("events", []):
        for comp in event.get("competitions", []):
            note = comp.get("altGameNote", "")
            if not any(m in note for m in _KNOCKOUT_MARKERS):
                continue
            if not comp.get("status", {}).get("type", {}).get("completed", False):
                continue
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue
            home = away = winner = ""
            home_goals = away_goals = 0
            for c in competitors:
                name = normalize(c["team"].get("displayName", ""))
                goals = int(c.get("score") or 0)
                if c.get("homeAway") == "home":
                    home, home_goals = name, goals
                else:
                    away, away_goals = name, goals
                if c.get("winner"):
                    winner = name
            if not (home and away and winner):
                continue
            out.append({
                "home": home, "away": away,
                "home_goals": home_goals, "away_goals": away_goals,
                "winner": winner,
            })
    return out
