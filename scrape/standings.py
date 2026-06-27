import json
import requests
from scrape.models import TeamStanding
from scrape.names import normalize
from scrape.cache import cache_get, cache_set

_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
_STAT_KEYS = {
    "gamesPlayed": "played",
    "wins": "won",
    "ties": "drawn",
    "losses": "lost",
    "pointsFor": "gf",
    "pointsAgainst": "ga",
    "pointDifferential": "gd",
    "points": "points",
}


def fetch_standings(use_cache: bool = True) -> list[TeamStanding]:
    try:
        raw = cache_get("standings") if use_cache else None
        if raw is None:
            r = requests.get(_URL, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            raw = r.text
            if use_cache:
                cache_set("standings", raw)
        return _parse(raw)
    except Exception:
        return []


def _parse(raw: str) -> list[TeamStanding]:
    data = json.loads(raw)
    result = []
    # ESPN API returns groups under data["children"], each child has child["standings"]["entries"]
    for child in data.get("children", []):
        group_name = child.get("name", "")
        group_letter = group_name.replace("Group ", "").strip()
        for entry in child.get("standings", {}).get("entries", []):
            team = normalize(entry["team"]["displayName"])
            stats: dict[str, int] = {}
            for stat in entry.get("stats", []):
                key = _STAT_KEYS.get(stat["name"])
                if key:
                    stats[key] = int(stat["value"])
            result.append(TeamStanding(
                group=group_letter,
                team=team,
                played=stats.get("played", 0),
                won=stats.get("won", 0),
                drawn=stats.get("drawn", 0),
                lost=stats.get("lost", 0),
                gf=stats.get("gf", 0),
                ga=stats.get("ga", 0),
                gd=stats.get("gd", 0),
                points=stats.get("points", 0),
            ))
    return result
