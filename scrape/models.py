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
