import json
import requests
from scrape.cache import cache_get, cache_set
from scrape.names import normalize

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
_DATES = ["20260628", "20260629", "20260630", "20260701", "20260702", "20260703", "20260704"]


def fetch_r32_slots(use_cache: bool = True) -> list[tuple[str, str]]:
    """
    Return the 16 R32 matchups as (home, away) pairs from the real ESPN bracket.
    Teams already known are canonical names; TBD slots use ESPN placeholder strings
    like 'Group L Winner' or 'Third Place Group E/H/I/J/K'.
    """
    try:
        raw = cache_get("r32_bracket") if use_cache else None
        if raw is None:
            slots = _scrape_r32_slots()
            raw = json.dumps(slots)
            if use_cache:
                cache_set("r32_bracket", raw)
        return [tuple(pair) for pair in json.loads(raw)]
    except Exception:
        return []


def _scrape_r32_slots() -> list[list[str]]:
    slots: list[list[str]] = []
    seen: set[str] = set()
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
        for event in data.get("events", []):
            for comp in event.get("competitions", []):
                if "Round of 32" not in comp.get("altGameNote", ""):
                    continue
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue
                home = away = ""
                for c in competitors:
                    name = c["team"].get("displayName", "")
                    # Normalize real team names; leave placeholder strings as-is
                    if not _is_placeholder(name):
                        name = normalize(name)
                    if c.get("homeAway") == "home":
                        home = name
                    else:
                        away = name
                key = f"{home}|{away}"
                if key not in seen:
                    seen.add(key)
                    slots.append([home, away])
    return slots


def _is_placeholder(name: str) -> bool:
    return "Group" in name or "Third Place" in name or "Place" in name
