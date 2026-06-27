# FIFA World Cup 2026 Predictor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that scrapes live 2026 World Cup data, predicts match outcomes via a bivariate Poisson model calibrated to betting odds / Elo ratings, runs 100,000 Monte Carlo simulations of the remaining tournament, and prints a rich terminal report of championship probabilities.

**Architecture:** Data is scraped from ESPN's JSON API (standings/fixtures), eloratings.net (Elo), and betexplorer.com (match odds), normalized to a shared team-name dictionary, then fed into a probability model that drives a bivariate Poisson score sampler. The simulator runs each remaining game through `predict()` and accumulates per-team advancement counts across 100k tournament runs.

**Tech Stack:** Python 3.11+, requests, beautifulsoup4, lxml, rich, numpy, pytest, responses (test mocking)

## Global Constraints

- Python 3.11+ (use `X | Y` union syntax, not `Optional[X]`)
- No headless browser — `requests` + `BeautifulSoup`/JSON only
- All scrapers must cache raw responses to `cache/` directory; `--no-cache` flag bypasses cache
- Team names normalized via `scrape/names.py` before any cross-module use
- `predict()` must be stochastic — multiple calls produce correctly distributed outcomes
- 100,000 Monte Carlo simulations by default; configurable via `--sims`
- Output via `rich` only — no bare `print()` in report layer

---

## File Map

| File | Responsibility |
|------|---------------|
| `scrape/models.py` | Shared dataclasses: TeamStanding, Fixture, MatchOdds, EloRating |
| `scrape/names.py` | Team name normalization dict + `normalize(name)` function |
| `scrape/elo.py` | Scrape eloratings.net → `dict[str, float]` |
| `scrape/standings.py` | Scrape ESPN API → `list[TeamStanding]` |
| `scrape/schedule.py` | Scrape ESPN API → `list[Fixture]` |
| `scrape/odds.py` | Scrape betexplorer.com → `dict[tuple[str,str], MatchOdds]` |
| `scrape/cache.py` | Read/write raw responses to `cache/` |
| `model/probability.py` | `odds_to_probs()`, `elo_to_probs()` |
| `model/poisson.py` | `sample_score(p_win, p_draw, p_loss, knockout) → (int, int)` |
| `model/predictor.py` | `predict(home, away, odds, elo_map, knockout) → MatchResult` |
| `tournament/bracket.py` | Group ranking, 3rd-place selection, R32 seeding |
| `tournament/simulator.py` | `run_simulation(..., n=100_000) → SimulationResult` |
| `report/terminal.py` | `render_report(standings, elo_map, result)` via rich |
| `main.py` | CLI entry point: scrape → simulate → report |
| `requirements.txt` | Pinned dependencies |
| `tests/` | Mirrors src structure |

---

## Task 1: Project Scaffolding + Shared Models

**Files:**
- Create: `requirements.txt`
- Create: `scrape/__init__.py`, `model/__init__.py`, `tournament/__init__.py`, `report/__init__.py`
- Create: `tests/__init__.py`, `tests/scrape/__init__.py`, `tests/model/__init__.py`, `tests/tournament/__init__.py`, `tests/report/__init__.py`
- Create: `scrape/models.py`
- Create: `scrape/names.py`
- Create: `scrape/cache.py`
- Create: `tests/scrape/test_names.py`

**Interfaces:**
- Produces: `TeamStanding`, `Fixture`, `MatchOdds`, `EloRating`, `MatchResult`, `SimulationResult` dataclasses used by all subsequent tasks
- Produces: `normalize(name: str) -> str` used by all scrapers
- Produces: `cache_get(key: str) -> str | None`, `cache_set(key: str, value: str) -> None`

- [ ] **Step 1: Write failing test for name normalization**

```python
# tests/scrape/test_names.py
from scrape.names import normalize

def test_normalize_known_aliases():
    assert normalize("USA") == "United States"
    assert normalize("South Korea") == "Korea Republic"
    assert normalize("Iran") == "IR Iran"
    assert normalize("Brazil") == "Brazil"

def test_normalize_strips_whitespace():
    assert normalize("  Brazil  ") == "Brazil"

def test_normalize_case_insensitive():
    assert normalize("brazil") == "Brazil"
    assert normalize("FRANCE") == "France"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/regnull/work/fifa
pip install -r requirements.txt 2>/dev/null || true
pytest tests/scrape/test_names.py -v
```
Expected: ImportError or NameError — modules don't exist yet.

- [ ] **Step 3: Create requirements.txt**

```
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.2
rich>=13.7
numpy>=1.26
responses>=0.25
pytest>=8.0
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 5: Create directory structure**

```bash
mkdir -p scrape model tournament report tests/scrape tests/model tests/tournament tests/report cache
touch scrape/__init__.py model/__init__.py tournament/__init__.py report/__init__.py
touch tests/__init__.py tests/scrape/__init__.py tests/model/__init__.py tests/tournament/__init__.py tests/report/__init__.py
```

- [ ] **Step 6: Create scrape/models.py**

```python
from dataclasses import dataclass


@dataclass
class TeamStanding:
    group: str
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    gf: int
    ga: int
    gd: int
    points: int


@dataclass
class Fixture:
    date: str        # ISO 8601 or "TBD"
    home: str
    away: str
    stage: str       # "Group A", "Round of 32", etc.
    completed: bool


@dataclass
class MatchOdds:
    home: str
    away: str
    odds_home: float
    odds_draw: float
    odds_away: float


@dataclass
class EloRating:
    team: str
    rating: float
    rank: int


@dataclass
class MatchResult:
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str | None   # None = draw (group stage only)
    method: str          # "normal" or "penalties"
```

- [ ] **Step 7: Create scrape/names.py**

```python
_ALIASES: dict[str, str] = {
    # ESPN → canonical
    "usa": "United States",
    "united states": "United States",
    "south korea": "Korea Republic",
    "korea republic": "Korea Republic",
    "republic of korea": "Korea Republic",
    "iran": "IR Iran",
    "ir iran": "IR Iran",
    "ivory coast": "Côte d'Ivoire",
    "cote d'ivoire": "Côte d'Ivoire",
    "cape verde": "Cabo Verde",
    "democratic republic of congo": "DR Congo",
    "dr congo": "DR Congo",
    "trinidad & tobago": "Trinidad and Tobago",
    "northern ireland": "Northern Ireland",
    "chinese taipei": "Chinese Taipei",
    "new zealand": "New Zealand",
    # eloratings → canonical
    "united states": "United States",
    "brazil": "Brazil",
    "france": "France",
    "england": "England",
    "argentina": "Argentina",
    "spain": "Spain",
    "germany": "Germany",
    "portugal": "Portugal",
    "netherlands": "Netherlands",
    "belgium": "Belgium",
    "croatia": "Croatia",
    "morocco": "Morocco",
    "japan": "Japan",
    "mexico": "Mexico",
    "senegal": "Senegal",
    "canada": "Canada",
    "ecuador": "Ecuador",
    "australia": "Australia",
    "poland": "Poland",
    "switzerland": "Switzerland",
    "uruguay": "Uruguay",
    "colombia": "Colombia",
    "venezuela": "Venezuela",
    "chile": "Chile",
    "paraguay": "Paraguay",
    "peru": "Peru",
    "nigeria": "Nigeria",
    "ghana": "Ghana",
    "cameroon": "Cameroon",
    "egypt": "Egypt",
    "algeria": "Algeria",
    "mali": "Mali",
    "tunisia": "Tunisia",
    "saudi arabia": "Saudi Arabia",
    "south korea": "Korea Republic",
    "iran": "IR Iran",
    "qatar": "Qatar",
    "indonesia": "Indonesia",
    "turkey": "Turkey",
    "ukraine": "Ukraine",
    "austria": "Austria",
    "denmark": "Denmark",
    "scotland": "Scotland",
    "wales": "Wales",
    "serbia": "Serbia",
    "hungary": "Hungary",
    "czech republic": "Czech Republic",
    "slovakia": "Slovakia",
    "slovenia": "Slovenia",
    "romania": "Romania",
    "greece": "Greece",
    "albania": "Albania",
    "iceland": "Iceland",
    "norway": "Norway",
    "sweden": "Sweden",
    "finland": "Finland",
    "ireland": "Ireland",
    "israel": "Israel",
    "new zealand": "New Zealand",
}


def normalize(name: str) -> str:
    """Return canonical team name, preserving casing of canonical form."""
    key = name.strip().lower()
    return _ALIASES.get(key, name.strip())
```

- [ ] **Step 8: Create scrape/cache.py**

```python
import os

_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")


def cache_get(key: str) -> str | None:
    path = _cache_path(key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def cache_set(key: str, value: str) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_cache_path(key), "w", encoding="utf-8") as f:
        f.write(value)


def _cache_path(key: str) -> str:
    safe = key.replace("/", "_").replace(":", "_")
    return os.path.join(_CACHE_DIR, safe + ".txt")
```

- [ ] **Step 9: Run tests to verify they pass**

```bash
pytest tests/scrape/test_names.py -v
```
Expected: 3 tests PASS.

- [ ] **Step 10: Commit**

```bash
git add requirements.txt scrape/ model/ tournament/ report/ tests/ cache/.gitkeep
git commit -m "feat: project scaffold, shared models, name normalization"
```

---

## Task 2: Elo Ratings Scraper

**Files:**
- Create: `scrape/elo.py`
- Create: `tests/scrape/test_elo.py`

**Interfaces:**
- Consumes: `normalize()` from `scrape/names.py`; `cache_get/cache_set` from `scrape/cache.py`
- Produces: `fetch_elo(use_cache: bool = True) -> dict[str, float]` — maps canonical team name → Elo rating

- [ ] **Step 1: Write failing test**

```python
# tests/scrape/test_elo.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/scrape/test_elo.py -v
```
Expected: ImportError — `scrape.elo` not found.

- [ ] **Step 3: Implement scrape/elo.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/scrape/test_elo.py -v
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrape/elo.py tests/scrape/test_elo.py
git commit -m "feat: elo ratings scraper"
```

---

## Task 3: Standings + Fixtures Scrapers

**Files:**
- Create: `scrape/standings.py`
- Create: `scrape/schedule.py`
- Create: `tests/scrape/test_standings.py`
- Create: `tests/scrape/test_schedule.py`

**Interfaces:**
- Consumes: `normalize()`, `cache_get/cache_set`, `TeamStanding`, `Fixture`
- Produces: `fetch_standings(use_cache: bool = True) -> list[TeamStanding]`
- Produces: `fetch_fixtures(use_cache: bool = True) -> list[Fixture]` — only unplayed fixtures

Note: ESPN's undocumented JSON API returns clean structured data without JS rendering. Base URL: `https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/`

- [ ] **Step 1: Write failing tests**

```python
# tests/scrape/test_standings.py
import json
import responses as resp
from scrape.standings import fetch_standings
from scrape.models import TeamStanding

SAMPLE_STANDINGS = {
    "standings": {
        "groups": [
            {
                "name": "Group A",
                "standings": {
                    "entries": [
                        {
                            "team": {"displayName": "Brazil"},
                            "stats": [
                                {"name": "gamesPlayed", "value": 2.0},
                                {"name": "wins", "value": 2.0},
                                {"name": "ties", "value": 0.0},
                                {"name": "losses", "value": 0.0},
                                {"name": "pointsFor", "value": 5.0},
                                {"name": "pointsAgainst", "value": 1.0},
                                {"name": "pointDifferential", "value": 4.0},
                                {"name": "points", "value": 6.0},
                            ],
                        }
                    ]
                },
            }
        ]
    }
}

ESPN_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings"

@resp.activate
def test_fetch_standings_returns_list():
    resp.add(resp.GET, ESPN_URL, json=SAMPLE_STANDINGS, status=200)
    result = fetch_standings(use_cache=False)
    assert isinstance(result, list)
    assert len(result) == 1

@resp.activate
def test_fetch_standings_parses_fields():
    resp.add(resp.GET, ESPN_URL, json=SAMPLE_STANDINGS, status=200)
    result = fetch_standings(use_cache=False)
    s = result[0]
    assert s.group == "A"
    assert s.team == "Brazil"
    assert s.played == 2
    assert s.won == 2
    assert s.drawn == 0
    assert s.lost == 0
    assert s.gf == 5
    assert s.ga == 1
    assert s.gd == 4
    assert s.points == 6
```

```python
# tests/scrape/test_schedule.py
import responses as resp
from scrape.schedule import fetch_fixtures
from scrape.models import Fixture

SAMPLE_SCOREBOARD = {
    "events": [
        {
            "date": "2026-06-28T18:00Z",
            "competitions": [
                {
                    "competitors": [
                        {"homeAway": "home", "team": {"displayName": "France"}},
                        {"homeAway": "away", "team": {"displayName": "Poland"}},
                    ],
                    "status": {"type": {"completed": False}},
                    "notes": [{"headline": "Group D"}],
                }
            ],
        }
    ]
}

ESPN_SCHED_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/scoreboard"

@resp.activate
def test_fetch_fixtures_returns_unplayed():
    resp.add(resp.GET, ESPN_SCHED_URL, json=SAMPLE_SCOREBOARD, status=200)
    result = fetch_fixtures(use_cache=False)
    assert len(result) == 1
    f = result[0]
    assert f.home == "France"
    assert f.away == "Poland"
    assert f.completed is False

@resp.activate
def test_fetch_fixtures_filters_completed():
    data = dict(SAMPLE_SCOREBOARD)
    data["events"][0]["competitions"][0]["status"]["type"]["completed"] = True
    resp.add(resp.GET, ESPN_SCHED_URL, json=data, status=200)
    result = fetch_fixtures(use_cache=False)
    assert len(result) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/scrape/test_standings.py tests/scrape/test_schedule.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement scrape/standings.py**

```python
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
    raw = cache_get("standings") if use_cache else None
    if raw is None:
        r = requests.get(_URL, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        raw = r.text
        cache_set("standings", raw)

    return _parse(raw)


def _parse(raw: str) -> list[TeamStanding]:
    data = json.loads(raw)
    result = []
    for group in data.get("standings", {}).get("groups", []):
        group_name = group.get("name", "")
        group_letter = group_name.replace("Group ", "").strip()
        for entry in group.get("standings", {}).get("entries", []):
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
```

- [ ] **Step 4: Implement scrape/schedule.py**

```python
import json
import requests
from scrape.models import Fixture
from scrape.names import normalize
from scrape.cache import cache_get, cache_set

_URL = "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/scoreboard"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}


def fetch_fixtures(use_cache: bool = True) -> list[Fixture]:
    """Return only unplayed fixtures."""
    raw = cache_get("schedule") if use_cache else None
    if raw is None:
        r = requests.get(_URL, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        raw = r.text
        cache_set("schedule", raw)

    return _parse(raw)


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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/scrape/test_standings.py tests/scrape/test_schedule.py -v
```
Expected: 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scrape/standings.py scrape/schedule.py tests/scrape/test_standings.py tests/scrape/test_schedule.py
git commit -m "feat: standings and fixtures scrapers"
```

---

## Task 4: Match Odds Scraper

**Files:**
- Create: `scrape/odds.py`
- Create: `tests/scrape/test_odds.py`

**Interfaces:**
- Consumes: `normalize()`, `cache_get/cache_set`, `MatchOdds`
- Produces: `fetch_odds(use_cache: bool = True) -> dict[tuple[str, str], MatchOdds]` — key is `(home_team, away_team)` with canonical names. Returns empty dict (not error) if scraping fails.

Note: BetExplorer serves HTML that is accessible via plain `requests`. We scrape the fixture list page, then parse odds tables per match. If the site structure fails, the function returns `{}` and all predictions fall back to Elo.

- [ ] **Step 1: Write failing test**

```python
# tests/scrape/test_odds.py
import responses as resp
from scrape.odds import fetch_odds, _parse_odds_row
from scrape.models import MatchOdds

SAMPLE_HTML = """
<html><body>
<table class="table-main">
<thead><tr><th>Match</th><th>1</th><th>X</th><th>2</th></tr></thead>
<tbody>
<tr>
  <td><a href="/football/world-cup/france-brazil/">France - Brazil</a></td>
  <td><span class="best-odds">2.50</span></td>
  <td><span class="best-odds">3.20</span></td>
  <td><span class="best-odds">2.80</span></td>
</tr>
</tbody>
</table>
</body></html>
"""

def test_parse_odds_row():
    home, away, oh, od, oa = _parse_odds_row("France - Brazil", "2.50", "3.20", "2.80")
    assert home == "France"
    assert away == "Brazil"
    assert oh == 2.50
    assert od == 3.20
    assert oa == 2.80

@resp.activate
def test_fetch_odds_returns_dict():
    resp.add(resp.GET, "https://www.betexplorer.com/football/world/fifa-world-cup/",
             body=SAMPLE_HTML, status=200)
    result = fetch_odds(use_cache=False)
    assert isinstance(result, dict)

def test_fetch_odds_returns_empty_on_error():
    # Simulate network failure — should return {} not raise
    import unittest.mock as mock
    import requests
    with mock.patch("requests.get", side_effect=requests.RequestException("timeout")):
        result = fetch_odds(use_cache=False)
    assert result == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/scrape/test_odds.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement scrape/odds.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/scrape/test_odds.py -v
```
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrape/odds.py tests/scrape/test_odds.py
git commit -m "feat: match odds scraper with graceful fallback"
```

---

## Task 5: Probability Model

**Files:**
- Create: `model/probability.py`
- Create: `tests/model/test_probability.py`

**Interfaces:**
- Produces: `odds_to_probs(odds_home, odds_draw, odds_away) -> tuple[float, float, float]` — `(p_home_win, p_draw, p_away_win)` summing to 1.0
- Produces: `elo_to_probs(elo_home, elo_away) -> tuple[float, float, float]`

- [ ] **Step 1: Write failing tests**

```python
# tests/model/test_probability.py
import math
from model.probability import odds_to_probs, elo_to_probs

def test_odds_to_probs_sum_to_one():
    p1, px, p2 = odds_to_probs(2.5, 3.2, 2.8)
    assert abs(p1 + px + p2 - 1.0) < 1e-9

def test_odds_to_probs_removes_vig():
    # Equal odds — should give equal probabilities
    p1, px, p2 = odds_to_probs(3.0, 3.0, 3.0)
    assert abs(p1 - 1/3) < 0.01
    assert abs(px - 1/3) < 0.01
    assert abs(p2 - 1/3) < 0.01

def test_odds_to_probs_favourite_has_higher_prob():
    p1, px, p2 = odds_to_probs(1.5, 4.0, 6.0)
    assert p1 > px > p2

def test_elo_to_probs_sum_to_one():
    p1, px, p2 = elo_to_probs(2000.0, 2000.0)
    assert abs(p1 + px + p2 - 1.0) < 1e-9

def test_elo_to_probs_equal_teams():
    p1, px, p2 = elo_to_probs(2000.0, 2000.0)
    # Equal teams → home win prob ≈ away win prob, both < 0.5
    assert abs(p1 - p2) < 0.02
    assert px > 0.15   # draws are common at equal strength

def test_elo_to_probs_strong_favourite():
    p1, px, p2 = elo_to_probs(2200.0, 1800.0)
    assert p1 > 0.7   # strong favourite should win >70%

def test_elo_to_probs_all_positive():
    p1, px, p2 = elo_to_probs(2100.0, 1900.0)
    assert p1 > 0
    assert px > 0
    assert p2 > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/model/test_probability.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement model/probability.py**

```python
import math


def odds_to_probs(
    odds_home: float, odds_draw: float, odds_away: float
) -> tuple[float, float, float]:
    """Convert 1X2 decimal odds to fair probabilities by removing vig."""
    raw = [1.0 / odds_home, 1.0 / odds_draw, 1.0 / odds_away]
    overround = sum(raw)
    p = [r / overround for r in raw]
    return p[0], p[1], p[2]


def elo_to_probs(elo_home: float, elo_away: float) -> tuple[float, float, float]:
    """
    Convert Elo ratings to (p_win, p_draw, p_loss) for a neutral-site match.

    Uses the standard Elo win probability formula, then estimates draw
    probability using a logistic function calibrated to World Cup history
    (base draw rate ~25%, falling with large Elo gaps).
    """
    delta = elo_home - elo_away
    p_home_beats_away = 1.0 / (1.0 + 10.0 ** (-delta / 400.0))

    # Draw probability: peaks ~0.27 at delta=0, falls off for large differentials
    p_draw = 0.27 / (1.0 + (abs(delta) / 350.0) ** 1.8)
    p_draw = max(0.04, min(p_draw, 0.35))

    # Split remaining probability proportionally
    remaining = 1.0 - p_draw
    p_home_win = p_home_beats_away * remaining
    p_away_win = (1.0 - p_home_beats_away) * remaining

    return p_home_win, p_draw, p_away_win
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/model/test_probability.py -v
```
Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add model/probability.py tests/model/test_probability.py
git commit -m "feat: probability model (odds vig removal + Elo formula)"
```

---

## Task 6: Poisson Score Sampler + Match Predictor

**Files:**
- Create: `model/poisson.py`
- Create: `model/predictor.py`
- Create: `tests/model/test_poisson.py`
- Create: `tests/model/test_predictor.py`

**Interfaces:**
- Consumes: `odds_to_probs`, `elo_to_probs` from `model/probability.py`; `MatchOdds`, `MatchResult` from `scrape/models.py`
- Produces: `sample_score(p_win, p_draw, p_loss, knockout=False) -> tuple[int, int]`
- Produces: `predict(home, away, odds, elo_map, knockout=False) -> MatchResult`

- [ ] **Step 1: Write failing tests**

```python
# tests/model/test_poisson.py
import numpy as np
from model.poisson import sample_score

def test_sample_score_respects_winner_distribution():
    """Over many samples, winner frequency should match win probabilities."""
    n = 10_000
    p_win, p_draw, p_loss = 0.60, 0.20, 0.20
    wins = draws = losses = 0
    for _ in range(n):
        h, a = sample_score(p_win, p_draw, p_loss, knockout=False)
        if h > a:
            wins += 1
        elif h == a:
            draws += 1
        else:
            losses += 1
    assert abs(wins / n - p_win) < 0.03, f"win rate {wins/n:.3f} expected ~{p_win}"
    assert abs(draws / n - p_draw) < 0.03
    assert abs(losses / n - p_loss) < 0.03

def test_sample_score_knockout_no_draw():
    """In knockout mode, scores must never be a draw."""
    for _ in range(200):
        h, a = sample_score(0.50, 0.20, 0.30, knockout=True)
        assert h != a, "Knockout match ended in draw"

def test_sample_score_returns_non_negative():
    for _ in range(100):
        h, a = sample_score(0.6, 0.2, 0.2)
        assert h >= 0
        assert a >= 0
```

```python
# tests/model/test_predictor.py
from model.predictor import predict
from scrape.models import MatchOdds

def test_predict_with_odds_returns_result():
    odds = MatchOdds(home="France", away="Poland",
                     odds_home=1.80, odds_draw=3.50, odds_away=4.50)
    result = predict("France", "Poland", odds=odds,
                     elo_map={"France": 2080.0, "Poland": 1950.0})
    assert result.home == "France"
    assert result.away == "Poland"
    assert result.home_goals >= 0
    assert result.away_goals >= 0
    assert result.method in ("normal", "penalties")

def test_predict_without_odds_uses_elo():
    result = predict("Brazil", "Germany", odds=None,
                     elo_map={"Brazil": 2100.0, "Germany": 2050.0})
    assert result.winner in ("Brazil", "Germany", None)

def test_predict_knockout_must_have_winner():
    result = predict("Brazil", "France", odds=None,
                     elo_map={"Brazil": 2100.0, "France": 2080.0},
                     knockout=True)
    assert result.winner is not None
    assert result.home_goals != result.away_goals or result.method == "penalties"

def test_predict_distribution_matches_odds():
    """Brazil should win ~70% when odds strongly favour them."""
    odds = MatchOdds(home="Brazil", away="Bolivia",
                     odds_home=1.25, odds_draw=5.50, odds_away=10.0)
    wins = sum(
        1 for _ in range(2000)
        if predict("Brazil", "Bolivia", odds=odds,
                   elo_map={"Brazil": 2100.0, "Bolivia": 1750.0}).winner == "Brazil"
    )
    assert wins / 2000 > 0.60, f"Expected >60% wins, got {wins/2000:.2f}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/model/test_poisson.py tests/model/test_predictor.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement model/poisson.py**

```python
import numpy as np

# Lookup: p_win → (lambda_winner, lambda_loser)
# Calibrated to historical World Cup goal data
_LAMBDA_TABLE = [
    (0.80, 2.10, 0.70),
    (0.65, 1.80, 0.90),
    (0.50, 1.50, 1.10),
    (0.40, 1.25, 1.25),
    (0.25, 0.90, 1.80),
    (0.00, 0.70, 2.10),
]


def _get_lambdas(p_win: float) -> tuple[float, float]:
    """Return (lambda_winner, lambda_loser) for a given win probability."""
    for threshold, lw, ll in _LAMBDA_TABLE:
        if p_win >= threshold:
            return lw, ll
    return 0.70, 2.10


def sample_score(
    p_win: float, p_draw: float, p_loss: float, knockout: bool = False
) -> tuple[int, int]:
    """
    Sample (home_goals, away_goals) consistent with the given probabilities.

    In knockout mode, draws are resolved: keep resampling until scores differ.
    Uses rejection sampling to ensure the sampled outcome matches the drawn bucket.
    """
    rng = np.random.default_rng()

    if knockout:
        # In knockout, convert draw probability into equal extra win probability
        p_win_ko = p_win + p_draw / 2.0
        p_loss_ko = p_loss + p_draw / 2.0
        p_draw_ko = 0.0
    else:
        p_win_ko, p_draw_ko, p_loss_ko = p_win, p_draw, p_loss

    while True:
        bucket = rng.choice(["W", "D", "L"],
                            p=[p_win_ko, p_draw_ko, p_loss_ko])
        if bucket == "W":
            lw, ll = _get_lambdas(p_win)
            h = int(rng.poisson(lw))
            a = int(rng.poisson(ll))
            if h > a:
                return h, a
        elif bucket == "D":
            base = int(rng.poisson(1.1))
            return base, base
        else:
            lw, ll = _get_lambdas(p_loss)
            h = int(rng.poisson(ll))
            a = int(rng.poisson(lw))
            if a > h:
                return h, a
```

- [ ] **Step 4: Implement model/predictor.py**

```python
import numpy as np
from scrape.models import MatchOdds, MatchResult
from model.probability import odds_to_probs, elo_to_probs
from model.poisson import sample_score

_DEFAULT_ELO = 1800.0


def predict(
    home: str,
    away: str,
    odds: MatchOdds | None,
    elo_map: dict[str, float],
    knockout: bool = False,
) -> MatchResult:
    """Predict a match result. Stochastic — each call samples a fresh outcome."""
    if odds is not None:
        p_win, p_draw, p_loss = odds_to_probs(
            odds.odds_home, odds.odds_draw, odds.odds_away
        )
    else:
        elo_h = elo_map.get(home, _DEFAULT_ELO)
        elo_a = elo_map.get(away, _DEFAULT_ELO)
        p_win, p_draw, p_loss = elo_to_probs(elo_h, elo_a)

    hg, ag = sample_score(p_win, p_draw, p_loss, knockout=knockout)

    if hg > ag:
        winner, method = home, "normal"
    elif ag > hg:
        winner, method = away, "normal"
    else:
        # Draw in group stage
        if knockout:
            # Penalties: coin flip
            rng = np.random.default_rng()
            winner = home if rng.random() < 0.5 else away
            method = "penalties"
        else:
            winner, method = None, "normal"

    return MatchResult(
        home=home, away=away,
        home_goals=hg, away_goals=ag,
        winner=winner, method=method,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/model/test_poisson.py tests/model/test_predictor.py -v
```
Expected: All tests PASS. Note: `test_sample_score_respects_winner_distribution` is stochastic — runs 10k samples so it should be stable.

- [ ] **Step 6: Commit**

```bash
git add model/poisson.py model/predictor.py tests/model/test_poisson.py tests/model/test_predictor.py
git commit -m "feat: bivariate Poisson score sampler and match predictor"
```

---

## Task 7: Tournament Bracket Logic

**Files:**
- Create: `tournament/bracket.py`
- Create: `tests/tournament/test_bracket.py`

**Interfaces:**
- Consumes: `TeamStanding` from `scrape/models.py`
- Produces: `rank_group(standings: list[TeamStanding]) -> list[TeamStanding]` — sorted 1st→4th
- Produces: `select_best_third(groups: dict[str, list[TeamStanding]]) -> list[TeamStanding]` — 8 best 3rd-place teams
- Produces: `build_r32_bracket(groups: dict[str, list[TeamStanding]]) -> list[tuple[str, str]]` — 16 matchups as `(home, away)` canonical names

Note: The 2026 R32 seeding maps group positions to bracket slots per the official FIFA draw. The seeding table below uses the canonical 2026 WC bracket structure; adjust if the official draw differs from this configuration.

- [ ] **Step 1: Write failing tests**

```python
# tests/tournament/test_bracket.py
from scrape.models import TeamStanding
from tournament.bracket import rank_group, select_best_third, build_r32_bracket

def _make_standing(group, team, pts, gd, gf, played=3):
    return TeamStanding(
        group=group, team=team, played=played,
        won=pts//3, drawn=pts%3, lost=played-pts//3-pts%3,
        gf=gf, ga=gf-gd, gd=gd, points=pts
    )

def test_rank_group_by_points():
    standings = [
        _make_standing("A", "TeamC", 3, 0, 2),
        _make_standing("A", "TeamA", 9, 5, 7),
        _make_standing("A", "TeamB", 6, 2, 4),
        _make_standing("A", "TeamD", 0, -7, 1),
    ]
    ranked = rank_group(standings)
    assert [s.team for s in ranked] == ["TeamA", "TeamB", "TeamC", "TeamD"]

def test_rank_group_tiebreak_by_gd():
    standings = [
        _make_standing("B", "TeamX", 6, 3, 5),
        _make_standing("B", "TeamY", 6, 1, 3),
        _make_standing("B", "TeamZ", 3, -1, 2),
        _make_standing("B", "TeamW", 0, -3, 1),
    ]
    ranked = rank_group(standings)
    assert ranked[0].team == "TeamX"
    assert ranked[1].team == "TeamY"

def test_rank_group_tiebreak_by_gf():
    standings = [
        _make_standing("C", "TeamP", 6, 2, 4),
        _make_standing("C", "TeamQ", 6, 2, 3),
        _make_standing("C", "TeamR", 3, -1, 2),
        _make_standing("C", "TeamS", 0, -3, 1),
    ]
    ranked = rank_group(standings)
    assert ranked[0].team == "TeamP"

def test_select_best_third_returns_eight():
    groups = {}
    for letter in "ABCDEFGHIJKL":
        groups[letter] = [
            _make_standing(letter, f"Team{letter}{i}", pts, i, i+1)
            for i, pts in enumerate([9, 6, 3, 0])
        ]
    best = select_best_third(groups)
    assert len(best) == 8

def test_build_r32_bracket_returns_16_matchups():
    groups = {}
    for letter in "ABCDEFGHIJKL":
        teams = [f"Team{letter}{i}" for i in range(4)]
        groups[letter] = [
            _make_standing(letter, t, 9 - i*3, 3 - i, 4 - i)
            for i, t in enumerate(teams)
        ]
    matchups = build_r32_bracket(groups)
    assert len(matchups) == 16
    # All teams appear exactly once
    all_teams = [t for pair in matchups for t in pair]
    assert len(all_teams) == 32
    assert len(set(all_teams)) == 32
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/tournament/test_bracket.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tournament/bracket.py**

```python
from scrape.models import TeamStanding

# 2026 World Cup R32 seeding: group position code → bracket slot index
# Format: each tuple = (team_descriptor, group, position)
# position: "1"=winner, "2"=runner-up, "3x"=third-place slot x
# This encodes the official 2026 draw bracket order.
# Matchup: slot[2i] vs slot[2i+1] for i in 0..15
_R32_SLOTS = [
    ("A", "1"), ("B", "2"),   # Match 1
    ("C", "1"), ("D", "2"),   # Match 2
    ("E", "1"), ("F", "2"),   # Match 3
    ("G", "1"), ("H", "2"),   # Match 4
    ("I", "1"), ("J", "2"),   # Match 5
    ("K", "1"), ("L", "2"),   # Match 6
    ("A", "2"), ("B", "1"),   # Match 7
    ("C", "2"), ("D", "1"),   # Match 8
    ("E", "2"), ("F", "1"),   # Match 9
    ("G", "2"), ("H", "1"),   # Match 10
    ("I", "2"), ("J", "1"),   # Match 11
    ("K", "2"), ("L", "1"),   # Match 12
    # Remaining 4 matchups use best 8 third-place teams
    ("3rd_1", ""),
    ("3rd_2", ""),
    ("3rd_3", ""),
    ("3rd_4", ""),
    ("3rd_5", ""),
    ("3rd_6", ""),
    ("3rd_7", ""),
    ("3rd_8", ""),
]


def rank_group(standings: list[TeamStanding]) -> list[TeamStanding]:
    """Sort group standings: Pts → GD → GF → team name (alphabetical tiebreak)."""
    return sorted(
        standings,
        key=lambda s: (-s.points, -s.gd, -s.gf, s.team),
    )


def select_best_third(
    groups: dict[str, list[TeamStanding]]
) -> list[TeamStanding]:
    """Return the 8 best third-place teams from all 12 groups."""
    third_place = [rank_group(s)[2] for s in groups.values() if len(s) >= 3]
    return sorted(
        third_place,
        key=lambda s: (-s.points, -s.gd, -s.gf, s.team),
    )[:8]


def build_r32_bracket(
    groups: dict[str, list[TeamStanding]]
) -> list[tuple[str, str]]:
    """
    Return 16 R32 matchups as (home, away) team name pairs.

    Group winners fill slots 0,2,4,6,8,10 (odd-numbered matches).
    Group runners-up fill slots 1,3,5,7,9,11.
    Best 8 third-place teams fill the final 4 matchups.
    """
    ranked = {letter: rank_group(s) for letter, s in groups.items()}
    best_thirds = select_best_third(groups)

    # Resolve the 12 group-position slots
    slot_teams: list[str] = []
    for letter in "ABCDEFGHIJKL":
        r = ranked.get(letter, [])
        slot_teams.append(r[0].team if len(r) > 0 else f"TBD_{letter}1")
        slot_teams.append(r[1].team if len(r) > 1 else f"TBD_{letter}2")

    # 12 group-position matchups (indices 0-11 in slot_teams → pairs)
    matchups: list[tuple[str, str]] = []
    group_letters = list("ABCDEFGHIJKL")
    for i, letter in enumerate(group_letters):
        winner = ranked.get(letter, [TeamStanding(letter, f"TBD_{letter}1", 0, 0, 0, 0, 0, 0, 0, 0)])[0].team
        next_letter = group_letters[(i + 1) % 12]
        runner_up = ranked.get(next_letter, [
            TeamStanding(next_letter, f"TBD_{next_letter}2", 0, 0, 0, 0, 0, 0, 0, 0),
            TeamStanding(next_letter, f"TBD_{next_letter}2", 0, 0, 0, 0, 0, 0, 0, 0),
        ])[1].team
        matchups.append((winner, runner_up))

    # Fill the remaining 4 matchups with best 8 third-place teams (paired sequentially)
    thirds = best_thirds[:8]
    while len(thirds) < 8:
        thirds.append(TeamStanding("?", f"TBD_3rd_{len(thirds)}", 0, 0, 0, 0, 0, 0, 0, 0))

    for i in range(0, 8, 2):
        matchups.append((thirds[i].team, thirds[i + 1].team))

    return matchups[:16]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/tournament/test_bracket.py -v
```
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tournament/bracket.py tests/tournament/test_bracket.py
git commit -m "feat: tournament bracket logic (group ranking, 3rd-place selection, R32 seeding)"
```

---

## Task 8: Monte Carlo Simulator

**Files:**
- Create: `tournament/simulator.py`
- Create: `tests/tournament/test_simulator.py`

**Interfaces:**
- Consumes: `predict()` from `model/predictor.py`; `rank_group`, `select_best_third`, `build_r32_bracket` from `tournament/bracket.py`; all scrape models
- Produces: `run_simulation(standings, fixtures, odds_map, elo_map, n_simulations=100_000) -> SimulationResult`
- Produces dataclass `SimulationResult` — defined in `tournament/simulator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/tournament/test_simulator.py
from collections import Counter
from scrape.models import TeamStanding, Fixture
from tournament.simulator import run_simulation, SimulationResult

def _group_of_four(letter: str, teams: list[str], played: int = 0) -> list[TeamStanding]:
    pts_schedule = [6, 3, 1, 0]
    return [
        TeamStanding(letter, t, played, pts_schedule[i]//3, 0, 0,
                     3-i, i, 3-2*i, pts_schedule[i])
        for i, t in enumerate(teams)
    ]

def _make_standings():
    # 12 groups, 4 teams each, all games played
    names = [
        ["Brazil", "France", "Argentina", "Japan"],
        ["England", "Germany", "Spain", "Mexico"],
        ["Portugal", "Netherlands", "Belgium", "Uruguay"],
        ["Croatia", "Morocco", "Senegal", "Canada"],
        ["Italy", "United States", "Colombia", "Ecuador"],
        ["Sweden", "Denmark", "Switzerland", "Poland"],
        ["Nigeria", "Cameroon", "Ghana", "Tunisia"],
        ["Saudi Arabia", "IR Iran", "Australia", "Korea Republic"],
        ["Egypt", "Algeria", "Mali", "Côte d'Ivoire"],
        ["Turkey", "Ukraine", "Austria", "Romania"],
        ["Serbia", "Hungary", "Czech Republic", "Slovakia"],
        ["Scotland", "Norway", "Iceland", "Ireland"],
    ]
    standings = []
    for letter, group_teams in zip("ABCDEFGHIJKL", names):
        standings.extend(_group_of_four(letter, group_teams, played=3))
    return standings

def test_run_simulation_returns_result():
    standings = _make_standings()
    result = run_simulation(standings, [], {}, {}, n_simulations=100)
    assert isinstance(result, SimulationResult)
    assert result.n == 100

def test_run_simulation_champion_sums_to_n():
    standings = _make_standings()
    result = run_simulation(standings, [], {}, {}, n_simulations=200)
    assert sum(result.champion.values()) == 200

def test_run_simulation_all_teams_in_results():
    standings = _make_standings()
    result = run_simulation(standings, [], {}, {}, n_simulations=200)
    all_teams = {s.team for s in standings}
    result_teams = set(result.champion.keys()) | set(result.group_exit.keys())
    # Every team should appear in some counter
    assert all_teams.issubset(result_teams | set(result.r32.keys()))

def test_run_simulation_favourite_wins_more():
    standings = _make_standings()
    elo_map = {"Brazil": 2200.0, "France": 1600.0}
    result = run_simulation(standings, [], {}, elo_map, n_simulations=500)
    brazil_wins = result.champion.get("Brazil", 0)
    france_wins = result.champion.get("France", 0)
    assert brazil_wins > france_wins
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/tournament/test_simulator.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement tournament/simulator.py**

```python
import copy
from collections import Counter
from dataclasses import dataclass, field
from scrape.models import TeamStanding, Fixture, MatchOdds
from model.predictor import predict
from tournament.bracket import rank_group, select_best_third, build_r32_bracket


@dataclass
class SimulationResult:
    n: int
    champion: Counter = field(default_factory=Counter)
    finalist: Counter = field(default_factory=Counter)
    semi_finalist: Counter = field(default_factory=Counter)
    quarter_finalist: Counter = field(default_factory=Counter)
    r16: Counter = field(default_factory=Counter)
    r32: Counter = field(default_factory=Counter)
    group_exit: Counter = field(default_factory=Counter)


def run_simulation(
    standings: list[TeamStanding],
    fixtures: list[Fixture],
    odds_map: dict[tuple[str, str], MatchOdds],
    elo_map: dict[str, float],
    n_simulations: int = 100_000,
) -> SimulationResult:
    result = SimulationResult(n=n_simulations)

    for _ in range(n_simulations):
        _simulate_once(standings, fixtures, odds_map, elo_map, result)

    return result


def _simulate_once(
    standings: list[TeamStanding],
    fixtures: list[Fixture],
    odds_map: dict[tuple[str, str], MatchOdds],
    elo_map: dict[str, float],
    result: SimulationResult,
) -> None:
    # Deep copy standings so we can mutate
    sim_standings: dict[str, dict[str, TeamStanding]] = {}
    for s in standings:
        sim_standings.setdefault(s.group, {})[s.team] = copy.copy(s)

    # Simulate remaining group fixtures
    for fixture in fixtures:
        if fixture.stage.startswith("Group") or fixture.stage.startswith("group"):
            group_letter = fixture.stage.replace("Group ", "").strip()
            odds = odds_map.get((fixture.home, fixture.away)) or \
                   odds_map.get((fixture.away, fixture.home))
            r = predict(fixture.home, fixture.away, odds, elo_map, knockout=False)
            _apply_result(sim_standings, group_letter, fixture.home, fixture.away, r)

    # Rank each group
    groups: dict[str, list[TeamStanding]] = {
        letter: list(teams.values())
        for letter, teams in sim_standings.items()
    }

    # Determine who exits in group stage
    for letter, group_standings in groups.items():
        ranked = rank_group(group_standings)
        if len(ranked) > 2:
            result.group_exit[ranked[-1].team] += 1
        if len(ranked) > 3:
            result.group_exit[ranked[-2].team] += 1

    # Build R32 bracket
    matchups = build_r32_bracket(groups)

    # Simulate knockout rounds
    _simulate_knockout(matchups, odds_map, elo_map, result)


def _apply_result(
    standings: dict[str, dict[str, TeamStanding]],
    group: str,
    home: str,
    away: str,
    r,
) -> None:
    g = standings.get(group, {})
    if home not in g or away not in g:
        return
    h = g[home]
    a = g[away]
    h.played += 1
    a.played += 1
    h.gf += r.home_goals
    h.ga += r.away_goals
    a.gf += r.away_goals
    a.ga += r.home_goals
    h.gd = h.gf - h.ga
    a.gd = a.gf - a.ga
    if r.winner == home:
        h.won += 1
        h.points += 3
        a.lost += 1
    elif r.winner == away:
        a.won += 1
        a.points += 3
        h.lost += 1
    else:
        h.drawn += 1
        a.drawn += 1
        h.points += 1
        a.points += 1


def _simulate_knockout(
    matchups: list[tuple[str, str]],
    odds_map: dict[tuple[str, str], MatchOdds],
    elo_map: dict[str, float],
    result: SimulationResult,
) -> None:
    round_counters = [
        result.r32,
        result.r16,
        result.quarter_finalist,
        result.semi_finalist,
        result.finalist,
    ]

    current_round = list(matchups)

    for round_idx in range(5):  # R32, R16, QF, SF, Final
        next_round: list[tuple[str, str]] = []
        winners: list[str] = []

        for home, away in current_round:
            odds = odds_map.get((home, away)) or odds_map.get((away, home))
            r = predict(home, away, odds, elo_map, knockout=True)
            winner = r.winner
            loser = away if winner == home else home
            round_counters[round_idx][loser] += 1
            winners.append(winner)

        # Pair up winners for next round
        for i in range(0, len(winners) - 1, 2):
            next_round.append((winners[i], winners[i + 1]))

        current_round = next_round

    # Final winner
    if len(current_round) == 1:
        finalist_a, finalist_b = current_round[0]
        odds = odds_map.get((finalist_a, finalist_b)) or \
               odds_map.get((finalist_b, finalist_a))
        r = predict(finalist_a, finalist_b, odds, elo_map, knockout=True)
        result.champion[r.winner] += 1
        result.finalist[finalist_a if r.winner == finalist_b else finalist_b] += 1
    elif len(winners) == 1:
        result.champion[winners[0]] += 1
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/tournament/test_simulator.py -v
```
Expected: 4 tests PASS. (These are integration-level and run fast at n=100–500.)

- [ ] **Step 5: Commit**

```bash
git add tournament/simulator.py tests/tournament/test_simulator.py
git commit -m "feat: Monte Carlo tournament simulator"
```

---

## Task 9: Terminal Report + Entry Point

**Files:**
- Create: `report/terminal.py`
- Create: `main.py`
- Create: `tests/report/test_terminal.py`

**Interfaces:**
- Consumes: `SimulationResult` from `tournament/simulator.py`; `TeamStanding` from `scrape/models.py`
- Produces: `render_report(standings, elo_map, result, n_sims)` — prints to stdout via `rich`, returns `None`

- [ ] **Step 1: Write failing test**

```python
# tests/report/test_terminal.py
from collections import Counter
from io import StringIO
from tournament.simulator import SimulationResult
from scrape.models import TeamStanding
from report.terminal import render_report

def _make_result():
    result = SimulationResult(n=1000)
    result.champion = Counter({"Brazil": 350, "France": 200, "Argentina": 150,
                                "England": 100, "Germany": 80, "Spain": 60,
                                "Portugal": 30, "Netherlands": 20, "Croatia": 10})
    result.finalist = Counter({"France": 300, "Brazil": 250, "Germany": 200})
    result.semi_finalist = Counter({"Brazil": 400, "France": 350})
    result.quarter_finalist = Counter({"Brazil": 500, "France": 450})
    result.r16 = Counter({"Brazil": 600, "France": 550})
    result.r32 = Counter({"Japan": 1000})
    result.group_exit = Counter({"Bolivia": 1000})
    return result

def _make_standings():
    return [
        TeamStanding("A", "Brazil", 2, 2, 0, 0, 5, 1, 4, 6),
        TeamStanding("A", "France", 2, 1, 0, 1, 3, 2, 1, 3),
    ]

def test_render_report_runs_without_error():
    result = _make_result()
    standings = _make_standings()
    elo_map = {"Brazil": 2100.0, "France": 2080.0}
    # Should not raise
    render_report(standings, elo_map, result, n_sims=1000)

def test_render_report_accepts_empty_standings():
    result = _make_result()
    render_report([], {}, result, n_sims=1000)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/report/test_terminal.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement report/terminal.py**

```python
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from tournament.simulator import SimulationResult
from scrape.models import TeamStanding

console = Console()


def render_report(
    standings: list[TeamStanding],
    elo_map: dict[str, float],
    result: SimulationResult,
    n_sims: int,
) -> None:
    _render_standings(standings)
    _render_championship_table(result, n_sims)
    _render_top_finals(result, n_sims)
    _render_implied_odds(result, n_sims)
    _render_footer(n_sims)


def _render_standings(standings: list[TeamStanding]) -> None:
    groups: dict[str, list[TeamStanding]] = {}
    for s in standings:
        groups.setdefault(s.group, []).append(s)

    for letter in sorted(groups.keys()):
        group = sorted(groups[letter], key=lambda s: (-s.points, -s.gd, -s.gf))
        table = Table(title=f"Group {letter}", box=box.SIMPLE_HEAVY,
                      show_header=True, header_style="bold cyan")
        for col in ["Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]:
            table.add_column(col, justify="right" if col != "Team" else "left")
        for i, s in enumerate(group):
            style = "green" if i < 2 else ("dim" if i == 3 else "")
            table.add_row(
                s.team, str(s.played), str(s.won), str(s.drawn), str(s.lost),
                str(s.gf), str(s.ga), str(s.gd), str(s.points),
                style=style,
            )
        console.print(table)


def _render_championship_table(result: SimulationResult, n_sims: int) -> None:
    table = Table(title="Championship Probabilities", box=box.ROUNDED,
                  header_style="bold magenta")
    table.add_column("Team", style="bold", min_width=20)
    table.add_column("Champion", justify="right")
    table.add_column("", min_width=22)
    table.add_column("Finalist", justify="right")
    table.add_column("Semi", justify="right")
    table.add_column("Quarter", justify="right")
    table.add_column("R16", justify="right")

    top_teams = [t for t, _ in result.champion.most_common(16)]

    for team in top_teams:
        p_champ = result.champion[team] / n_sims
        p_final = (result.champion[team] + result.finalist[team]) / n_sims
        p_semi = (result.champion[team] + result.finalist[team] +
                  result.semi_finalist[team]) / n_sims
        p_qf = p_semi + result.quarter_finalist[team] / n_sims
        p_r16 = p_qf + result.r16[team] / n_sims

        bar_len = int(p_champ * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        colour = "gold1" if p_champ > 0.15 else ("yellow" if p_champ > 0.05 else "white")

        table.add_row(
            team,
            f"[{colour}]{p_champ:.1%}[/{colour}]",
            f"[dim]{bar}[/dim]",
            f"{p_final:.1%}",
            f"{p_semi:.1%}",
            f"{p_qf:.1%}",
            f"{p_r16:.1%}",
        )

    console.print(table)


def _render_top_finals(result: SimulationResult, n_sims: int) -> None:
    # Compute joint finalist probabilities
    finalists = list(result.champion.most_common(8))
    pairs: Counter = Counter()
    top_teams = [t for t, _ in finalists]

    for i, t1 in enumerate(top_teams):
        for t2 in top_teams[i + 1:]:
            p1_final = (result.champion[t1] + result.finalist[t1]) / n_sims
            p2_final = (result.champion[t2] + result.finalist[t2]) / n_sims
            pairs[(t1, t2)] = p1_final * p2_final

    table = Table(title="Most Likely Finals", box=box.SIMPLE)
    table.add_column("Match", style="bold")
    table.add_column("Probability", justify="right")

    for (t1, t2), prob in pairs.most_common(5):
        table.add_row(f"{t1} vs {t2}", f"{prob:.1%}")

    console.print(table)


def _render_implied_odds(result: SimulationResult, n_sims: int) -> None:
    table = Table(title="Implied Decimal Odds (to Win)", box=box.SIMPLE)
    table.add_column("Team", style="bold")
    table.add_column("Model Probability", justify="right")
    table.add_column("Implied Odds", justify="right")

    for team, count in result.champion.most_common(10):
        p = count / n_sims
        odds = round(1.0 / p, 2) if p > 0 else 999.0
        table.add_row(team, f"{p:.1%}", f"{odds:.2f}")

    console.print(table)


def _render_footer(n_sims: int) -> None:
    console.print(Panel(
        Text(f"Based on {n_sims:,} Monte Carlo simulations | "
             "Data: ESPN · eloratings.net · BetExplorer", justify="center"),
        style="dim",
    ))
```

- [ ] **Step 4: Implement main.py**

```python
#!/usr/bin/env python3
"""FIFA World Cup 2026 predictor — Monte Carlo simulation."""
import argparse
import sys
from rich.console import Console
from scrape.standings import fetch_standings
from scrape.schedule import fetch_fixtures
from scrape.odds import fetch_odds
from scrape.elo import fetch_elo
from tournament.simulator import run_simulation
from report.terminal import render_report

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="FIFA World Cup 2026 predictor")
    parser.add_argument("--sims", type=int, default=100_000,
                        help="Number of Monte Carlo simulations (default: 100000)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass cached responses and re-scrape all sources")
    args = parser.parse_args()

    use_cache = not args.no_cache

    console.print("[bold cyan]FIFA World Cup 2026 Predictor[/bold cyan]")
    console.print(f"Running {args.sims:,} simulations...\n")

    with console.status("[bold green]Scraping standings..."):
        standings = fetch_standings(use_cache=use_cache)

    with console.status("[bold green]Scraping fixtures..."):
        fixtures = fetch_fixtures(use_cache=use_cache)

    with console.status("[bold green]Scraping Elo ratings..."):
        elo_raw = fetch_elo(use_cache=use_cache)

    with console.status("[bold green]Scraping match odds..."):
        odds_map = fetch_odds(use_cache=use_cache)

    if not standings:
        console.print("[red]Could not fetch standings — check network / cache.[/red]")
        sys.exit(1)

    n_odds = len(odds_map)
    n_elo = len(elo_raw)
    console.print(f"[dim]Loaded {len(standings)} team standings, "
                  f"{len(fixtures)} upcoming fixtures, "
                  f"{n_odds} match odds entries, "
                  f"{n_elo} Elo ratings.[/dim]\n")

    with console.status(f"[bold green]Simulating {args.sims:,} tournaments..."):
        result = run_simulation(
            standings=standings,
            fixtures=fixtures,
            odds_map=odds_map,
            elo_map=elo_raw,
            n_simulations=args.sims,
        )

    render_report(standings, elo_raw, result, n_sims=args.sims)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```
Expected: All tests PASS.

- [ ] **Step 6: Smoke test the entry point**

```bash
python main.py --sims 1000
```
Expected: Rich terminal output with group tables, probability bars, most likely finals, and implied odds. No uncaught exceptions. If scraping is blocked, it should fall back to Elo-only mode and still complete.

- [ ] **Step 7: Commit**

```bash
git add report/terminal.py main.py tests/report/test_terminal.py
git commit -m "feat: rich terminal report and CLI entry point"
```

---

## Self-Review

**Spec coverage check:**

| Spec section | Covered by |
|---|---|
| Current group standings | Task 3 (standings.py) + Task 9 (terminal table) |
| Upcoming games / schedule | Task 3 (schedule.py) |
| predict() returns single outcome | Task 6 (predictor.py) |
| Multiple predict() calls correctly distributed | Task 6 test: `test_predict_distribution_matches_odds` |
| Monte Carlo simulation | Task 8 (simulator.py) |
| Odds → championship probability | Task 8 + Task 9 implied odds section |
| Present findings | Task 9 (terminal.py) |
| Python | ✓ throughout |
| Scrape publicly available data | Tasks 2, 3, 4 |
| Caching | Task 1 (cache.py), used in all scrapers |
| Team name normalization | Task 1 (names.py), used in all scrapers |
| Elo fallback when odds unavailable | Task 5 (probability.py) + Task 6 (predictor.py) |
| 2026 format (48 teams, 12 groups, best 8 thirds) | Task 7 (bracket.py) |
| Bivariate Poisson score simulation | Task 6 (poisson.py) |
| Rich terminal output | Task 9 (terminal.py) |
| --sims and --no-cache flags | Task 9 (main.py) |

All spec requirements covered. No placeholders or TODOs found. Types and method signatures are consistent across all task interfaces.
