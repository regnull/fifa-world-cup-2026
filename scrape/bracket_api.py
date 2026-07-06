import json
import re
import requests
from scrape.cache import cache_get, cache_set, LIVE_TTL
from scrape.names import normalize

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
# R32 runs Jun 28 – Jul 3; R16 Jul 4–7; QF Jul 9–11. The later rounds are
# scraped for their pairings, which encode the bracket tree.
_DATES = ["20260628", "20260629", "20260630", "20260701", "20260702", "20260703",
          "20260704", "20260705", "20260706", "20260707",
          "20260709", "20260710", "20260711"]
_ROUND_MARKERS = {"Round of 32": "r32", "Round of 16": "r16", "Quarterfinal": "qf"}


def fetch_r32_slots(use_cache: bool = True) -> list[tuple[str, str]]:
    """
    Return the 16 R32 matchups as (home, away) pairs from the real ESPN bracket,
    ordered so that pairing winners sequentially reproduces the real knockout
    tree (R32 games are scheduled in an order that differs from bracket order).
    Teams already known are canonical names; TBD slots use ESPN placeholder
    strings like 'Group L Winner' or 'Third Place Group E/H/I/J/K'.
    """
    try:
        raw = cache_get("r32_bracket", max_age=LIVE_TTL) if use_cache else None
        if raw is None:
            rounds = _scrape_rounds()
            slots = order_slots_by_bracket(rounds["r32"], rounds["r16"], rounds["qf"])
            raw = json.dumps(slots)
            if use_cache:
                cache_set("r32_bracket", raw)
        return [tuple(pair) for pair in json.loads(raw)]
    except Exception:
        return []


def _scrape_rounds() -> dict[str, list[tuple[str, str]]]:
    """Scrape R32/R16/QF matchups, each list in ESPN schedule order."""
    rounds: dict[str, list[tuple[str, str]]] = {"r32": [], "r16": [], "qf": []}
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
                note = comp.get("altGameNote", "")
                round_key = next(
                    (k for m, k in _ROUND_MARKERS.items() if m in note), None
                )
                if round_key is None:
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
                key = f"{round_key}|{home}|{away}"
                if key not in seen:
                    seen.add(key)
                    rounds[round_key].append((home, away))
    return rounds


def order_slots_by_bracket(
    r32_slots: list[tuple[str, str]],
    r16_pairs: list[tuple[str, str]],
    qf_pairs: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """
    Reorder the 16 R32 games (ESPN schedule order) into bracket order, so that
    pairing winners sequentially reproduces the real R16 games, quarterfinals,
    and semifinals.

    ``r16_pairs``/``qf_pairs`` are the later rounds' matchups in ESPN schedule
    order; sides are team names or placeholders like 'Round of 16 6 Winner'.
    ESPN chains rounds sequentially from the R16 onward (QF #1 is R16 #1 winner
    vs R16 #2 winner, SF #1 is QF #1 winner vs QF #2 winner, ...), so only the
    R32 -> R16 mapping needs to be derived from the pairings. Returns the slots
    unchanged if the structure can't be resolved (e.g. R16 not yet scheduled).
    """
    if len(r32_slots) != 16 or len(r16_pairs) != 8 or len(qf_pairs) != 4:
        return r32_slots

    def game_index(name: str, pairs: list[tuple[str, str]], round_no: int) -> int | None:
        m = re.match(rf"Round of {round_no} (\d+) Winner", name)
        if m:
            idx = int(m.group(1)) - 1
            return idx if 0 <= idx < len(pairs) else None
        return next((i for i, pair in enumerate(pairs) if name in pair), None)

    ordered: list[tuple[str, str]] = []
    for qf in qf_pairs:
        for side in qf:
            r16_idx = game_index(side, r16_pairs, 16)
            if r16_idx is None:
                return r32_slots
            for team in r16_pairs[r16_idx]:
                r32_idx = game_index(team, r32_slots, 32)
                if r32_idx is None:
                    return r32_slots
                ordered.append(r32_slots[r32_idx])

    if sorted(map(sorted, ordered)) != sorted(map(sorted, r32_slots)):
        return r32_slots
    return ordered


def _is_placeholder(name: str) -> bool:
    return "Group" in name or "Third Place" in name or "Place" in name
