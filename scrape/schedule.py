import json
import requests
from scrape.models import Fixture
from scrape.names import normalize
from scrape.cache import cache_get, cache_set, LIVE_TTL

_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}


def fetch_fixtures(use_cache: bool = True) -> list[Fixture]:
    """Return only unplayed fixtures."""
    try:
        raw = cache_get("schedule", max_age=LIVE_TTL) if use_cache else None
        if raw is None:
            r = requests.get(_URL, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            raw = r.text
            if use_cache:
                cache_set("schedule", raw)
        return _parse(raw)
    except Exception:
        return []


def _parse(raw: str) -> list[Fixture]:
    data = json.loads(raw)
    result = []
    for event in data.get("events", []):
        date = event.get("date", "TBD")
        for comp in event.get("competitions", []):
            completed = comp.get("status", {}).get("type", {}).get("completed", False)
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
            # altGameNote e.g. "FIFA World Cup, Group L" → "Group L"
            note = comp.get("altGameNote", "")
            if "Group" in note:
                stage = note.split(", ", 1)[-1]  # "Group L"
            elif data.get("season", {}).get("slug", "").lower() == "group-stage":
                stage = "Group"
            else:
                notes = comp.get("notes", [])
                stage = notes[0].get("headline", "Unknown") if notes else "Unknown"
            result.append(Fixture(
                date=date,
                home=home,
                away=away,
                stage=stage,
                completed=completed,
            ))
    return [f for f in result if not f.completed]
