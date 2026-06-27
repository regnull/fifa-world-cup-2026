# FIFA World Cup 2026 Predictor — Design Spec

**Date:** 2026-06-27  
**Status:** Approved  
**Context:** The 2026 FIFA World Cup is currently in progress (group stage). This tool scrapes live data, simulates the remaining tournament 100,000 times, and reports championship probabilities via terminal output.

---

## 1. Goals

- Ingest live group standings, remaining fixtures, match odds, and Elo ratings via web scraping
- Predict individual match outcomes using a probabilistic model (odds-first, Elo fallback)
- Run a full Monte Carlo simulation of the remaining tournament
- Present findings as rich terminal output: probability bars, tables, most-likely final

---

## 2. Project Structure

```
fifa/
├── scrape/
│   ├── __init__.py
│   ├── standings.py     # ESPN group standings
│   ├── schedule.py      # Remaining fixtures
│   ├── odds.py          # OddsPortal 1X2 match odds
│   └── elo.py           # eloratings.net Elo ratings
├── model/
│   ├── __init__.py
│   ├── probability.py   # Odds → implied probability (vig removal); Elo → probability
│   ├── poisson.py       # Bivariate Poisson score sampler
│   └── predictor.py     # predict(team_a, team_b) → MatchResult
├── tournament/
│   ├── __init__.py
│   ├── bracket.py       # 2026 WC bracket logic (12 groups → R32 → Final)
│   └── simulator.py     # Monte Carlo runner
├── report/
│   ├── __init__.py
│   └── terminal.py      # Rich-based terminal report
├── main.py              # Entry point
└── requirements.txt
```

---

## 3. Data Layer

### 3.1 Group Standings — `scrape/standings.py`

**Source:** `https://www.espn.com/soccer/standings/_/league/FIFA.WORLD`  
**Method:** `requests` + `BeautifulSoup`, parse HTML tables  
**Output schema:**

```python
@dataclass
class TeamStanding:
    group: str          # "A", "B", ..., "L"
    team: str           # Normalized team name, e.g. "Brazil"
    played: int
    won: int
    drawn: int
    lost: int
    gf: int             # Goals for
    ga: int             # Goals against
    gd: int             # Goal difference
    points: int
```

### 3.2 Remaining Fixtures — `scrape/schedule.py`

**Source:** `https://www.espn.com/soccer/schedule/_/league/FIFA.WORLD`  
**Method:** `requests` + `BeautifulSoup`  
**Output schema:**

```python
@dataclass
class Fixture:
    date: str           # ISO 8601
    home: str           # Normalized team name
    away: str           # Normalized team name
    stage: str          # "Group A", "Round of 32", etc.
    completed: bool     # True if score already recorded
```

Only unplayed fixtures (`completed=False`) are passed to the simulator.

### 3.3 Match Odds — `scrape/odds.py`

**Source:** `https://www.oddsportal.com/football/world/fifa-world-cup/`  
**Method:** `requests` with browser-like headers + `BeautifulSoup`  
**Output schema:**

```python
@dataclass
class MatchOdds:
    home: str
    away: str
    odds_home: float    # Decimal odds for home win
    odds_draw: float
    odds_away: float
    source: str         # Bookmaker name or "avg"
```

Returns `None` for fixtures where odds are not yet posted (far-future rounds). Falls back to Elo model in that case.

### 3.4 Elo Ratings — `scrape/elo.py`

**Source:** `https://www.eloratings.net/`  
**Method:** `requests` + `BeautifulSoup`, parse the ratings table  
**Output schema:**

```python
@dataclass
class EloRating:
    team: str
    rating: float       # e.g. 2083.0 for Brazil
    rank: int
```

Team names are normalized to match ESPN naming via a shared lookup dict.

---

## 4. Match Prediction Model

### 4.1 Implied Probability — `model/probability.py`

Given 1X2 odds, remove the bookmaker overround to get fair probabilities:

```
raw_i = 1 / odds_i
overround = sum(raw_i)
p_i = raw_i / overround
```

Output: `(p_home_win, p_draw, p_away_win)` summing to 1.0.

When only Elo ratings are available:

```
p_home_win = 1 / (1 + 10^(-(elo_home - elo_away + HOME_ADVANTAGE) / 400))
```

`HOME_ADVANTAGE = 0` for neutral-site World Cup games.

Draw probability is estimated using a logistic function calibrated to historical World Cup data (approx. 25% base draw rate, declining at large Elo differentials). Loss probability fills the remainder.

### 4.2 Expected Goals — `model/poisson.py`

Convert `(p_win, p_draw, p_loss)` to expected goals `(λ_home, λ_away)` via a pre-computed lookup table derived from historical World Cup match data:

| p_home_win | λ_home | λ_away |
|------------|--------|--------|
| 0.80+      | 2.10   | 0.70   |
| 0.65–0.80  | 1.80   | 0.90   |
| 0.50–0.65  | 1.50   | 1.10   |
| 0.40–0.50  | 1.25   | 1.25   |
| 0.25–0.40  | 0.90   | 1.80   |
| < 0.25     | 0.70   | 2.10   |

When the away team is the favorite, p_away_win drives λ_away selection symmetrically (swap columns).

Actual goals are sampled from `Poisson(λ_home)` and `Poisson(λ_away)` independently. If the sampled outcome contradicts the drawn win/draw/loss bucket, resample (rejection sampling). This preserves score realism while respecting the probability distribution.

For knockout rounds: draws lead to a penalty shootout. Penalty win probability is 0.50 for each team (coin flip).

### 4.3 Predictor — `model/predictor.py`

```python
@dataclass
class MatchResult:
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str | None  # None on draw (group stage only)
    method: str         # "normal", "penalties"

def predict(home: str, away: str, odds: MatchOdds | None,
            elo: dict[str, float], knockout: bool = False) -> MatchResult:
    ...
```

- `knockout=True` forces a winner (no draws; extra time + penalties if needed)
- Multiple calls produce correctly distributed outcomes across the probability space

---

## 5. Tournament Bracket Logic — `tournament/bracket.py`

### 5.1 2026 Format

- **48 teams** in **12 groups** of 4 (Groups A–L)
- **Group stage advancement:**
  - Top 2 from each group → 24 automatic qualifiers
  - Best 8 third-place teams (ranked by Pts → GD → GF → disciplinary) → 8 more qualifiers
  - Total: 32 teams in Round of 32
- **Knockout rounds:** R32 → R16 → QF (8) → SF (4) → Final + 3rd place

### 5.2 R32 Seeding

The official FIFA bracket pre-determines R32 matchups based on group position. The seeding table maps group winners/runners-up/third-place slots to specific R32 slots. This table is hardcoded from the official draw.

### 5.3 Group Simulation

For each unplayed group game, call `predict()` to get a result, update standings, then rank the final group table by Pts → GD → GF → head-to-head.

---

## 6. Monte Carlo Simulator — `tournament/simulator.py`

```python
def run_simulation(
    standings: list[TeamStanding],
    fixtures: list[Fixture],
    odds_map: dict[tuple[str, str], MatchOdds],
    elo_map: dict[str, float],
    n_simulations: int = 100_000,
) -> SimulationResult:
    ...
```

Each simulation:
1. Copy current standings
2. Simulate all remaining group stage games
3. Rank each group; determine the 8 best third-place teams
4. Seed the R32 bracket
5. Simulate R32 → R16 → QF → SF → Final (knockout, `predict()` with `knockout=True`)
6. Record the winner and each team's exit round

Accumulate across all simulations:

```python
@dataclass
class SimulationResult:
    n: int
    champion: Counter[str]       # team → win count
    finalist: Counter[str]
    semi_finalist: Counter[str]
    quarter_finalist: Counter[str]
    r16: Counter[str]
    r32: Counter[str]
    group_exit: Counter[str]
```

---

## 7. Terminal Report — `report/terminal.py`

Uses the `rich` library. Output sections (in order):

### 7.1 Current Group Standings
One table per active group showing current P/W/D/L/GF/GA/GD/Pts. Teams on track to qualify shown in green; eliminated shown in dim.

### 7.2 Championship Probability Table
Top 16 teams ranked by `p_champion`, with progress bars for each round:

```
Team           Champion  Final    Semi    QF      R16
Brazil         38.2% ██  52.1%    68.4%   81.2%   94.1%
France         22.1% █   38.5%    55.2%   72.3%   91.0%
...
```

### 7.3 Most Likely Final
Top 5 most probable finals (pairing × joint probability).

### 7.4 Implied Odds
Championship probabilities converted back to decimal odds for quick reference (e.g., Brazil 38.2% → 2.62).

### 7.5 Simulation Stats
Number of simulations run, data freshness timestamps, model notes (which games used odds vs Elo).

---

## 8. Entry Point — `main.py`

```
python main.py [--sims 100000] [--no-cache]
```

1. Scrape all data sources (with 60s timeout, retry ×3)
2. Cache raw responses to `cache/` (skip re-scrape unless `--no-cache`)
3. Normalize team names across sources
4. Run simulation
5. Print report

---

## 9. Dependencies

```
requests>=2.31
beautifulsoup4>=4.12
lxml>=5.0
rich>=13.0
numpy>=1.26
scipy>=1.12
```

No external paid APIs. No headless browser (JS-free scraping only).

---

## 10. Team Name Normalization

A shared mapping dict (`scrape/names.py`) resolves inconsistencies across ESPN, OddsPortal, and eloratings.net (e.g., `"USA"` → `"United States"`, `"South Korea"` → `"Korea Republic"`).

---

## 11. Out of Scope

- Historical backtesting
- Live score updates / auto-refresh
- HTML report output
- Player-level statistics
- Betting recommendation engine
