import copy
from collections import Counter
from dataclasses import dataclass, field
from scrape.models import TeamStanding, Fixture, MatchOdds
from model.predictor import predict
from tournament.bracket import rank_group, select_best_third, build_r32_bracket, resolve_r32_bracket


@dataclass
class RoundTrace:
    name: str
    games: list  # list[MatchResult]


@dataclass
class TournamentTrace:
    group_games: list       # list[MatchResult] — only simulated (not already played)
    rounds: list[RoundTrace]
    champion: str


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
    r32_slots: list[tuple[str, str]] | None = None,
    progress=None,
    task_id=None,
) -> SimulationResult:
    result = SimulationResult(n=n_simulations)

    for _ in range(n_simulations):
        _simulate_once(standings, fixtures, odds_map, elo_map, result, r32_slots)
        if progress is not None and task_id is not None:
            progress.advance(task_id)

    return result


def _simulate_once(
    standings: list[TeamStanding],
    fixtures: list[Fixture],
    odds_map: dict[tuple[str, str], MatchOdds],
    elo_map: dict[str, float],
    result: SimulationResult,
    r32_slots: list[tuple[str, str]] | None = None,
) -> None:
    # Copy standings into mutable per-group dicts
    sim_standings: dict[str, dict[str, TeamStanding]] = {}
    for s in standings:
        sim_standings.setdefault(s.group, {})[s.team] = copy.copy(s)

    # Simulate remaining group-stage fixtures
    for fixture in fixtures:
        if fixture.stage.lower().startswith("group"):
            # Extract the group letter: "Group A" -> "A"
            group_letter = fixture.stage.split()[-1].strip()
            odds = odds_map.get((fixture.home, fixture.away)) or \
                   odds_map.get((fixture.away, fixture.home))
            r = predict(fixture.home, fixture.away, odds, elo_map, knockout=False)
            _apply_result(sim_standings, group_letter, fixture.home, fixture.away, r)

    # Build ranked groups
    groups: dict[str, list[TeamStanding]] = {
        letter: list(teams.values())
        for letter, teams in sim_standings.items()
    }

    # Mark 4th-place teams as group exits (all 12)
    for group_standings in groups.values():
        ranked = rank_group(group_standings)
        if len(ranked) >= 4:
            result.group_exit[ranked[3].team] += 1

    # Mark 3rd-place teams that do NOT advance as group exits
    all_thirds = [rank_group(s)[2] for s in groups.values() if len(s) >= 3]
    advancing_thirds = {t.team for t in select_best_third(groups)}
    for t in all_thirds:
        if t.team not in advancing_thirds:
            result.group_exit[t.team] += 1

    # Build R32 bracket and simulate knockout rounds
    if r32_slots:
        matchups = resolve_r32_bracket(r32_slots, groups)
    else:
        matchups = build_r32_bracket(groups)
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
    # round_counters[i] records the loser of each round (i.e. who exits at that stage)
    round_counters = [
        result.r32,           # Round 0: R32 losers exit at R32
        result.r16,           # Round 1: R16 losers exit at R16
        result.quarter_finalist,  # Round 2: QF losers
        result.semi_finalist,     # Round 3: SF losers
        result.finalist,          # Round 4: Final loser
    ]

    current_round = list(matchups)

    for round_idx in range(5):  # R32, R16, QF, SF, Final
        winners: list[str] = []

        for home, away in current_round:
            odds = odds_map.get((home, away)) or odds_map.get((away, home))
            r = predict(home, away, odds, elo_map, knockout=True)
            winner = r.winner
            loser = away if winner == home else home
            round_counters[round_idx][loser] += 1
            winners.append(winner)

        if round_idx == 4:
            # After the final, the sole winner is the champion
            if winners:
                result.champion[winners[0]] += 1
            break

        # Pair up winners for next round
        next_round: list[tuple[str, str]] = []
        for i in range(0, len(winners) - 1, 2):
            next_round.append((winners[i], winners[i + 1]))
        current_round = next_round


def simulate_trace(
    standings: list[TeamStanding],
    fixtures: list[Fixture],
    odds_map: dict[tuple[str, str], MatchOdds],
    elo_map: dict[str, float],
    r32_slots: list[tuple[str, str]] | None = None,
) -> TournamentTrace:
    """Run one full tournament simulation and return every game result."""
    sim_standings: dict[str, dict[str, TeamStanding]] = {}
    for s in standings:
        sim_standings.setdefault(s.group, {})[s.team] = copy.copy(s)

    group_games = []
    for fixture in fixtures:
        if fixture.stage.lower().startswith("group"):
            group_letter = fixture.stage.split()[-1].strip()
            odds = odds_map.get((fixture.home, fixture.away)) or \
                   odds_map.get((fixture.away, fixture.home))
            r = predict(fixture.home, fixture.away, odds, elo_map, knockout=False)
            _apply_result(sim_standings, group_letter, fixture.home, fixture.away, r)
            group_games.append(r)

    groups: dict[str, list[TeamStanding]] = {
        letter: list(teams.values())
        for letter, teams in sim_standings.items()
    }

    if r32_slots:
        matchups = resolve_r32_bracket(r32_slots, groups)
    else:
        matchups = build_r32_bracket(groups)

    round_names = ["Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final"]
    rounds: list[RoundTrace] = []
    current_round = list(matchups)
    champion = ""

    for round_idx in range(5):
        games = []
        winners: list[str] = []
        for home, away in current_round:
            odds = odds_map.get((home, away)) or odds_map.get((away, home))
            r = predict(home, away, odds, elo_map, knockout=True)
            games.append(r)
            winners.append(r.winner)
        rounds.append(RoundTrace(name=round_names[round_idx], games=games))
        if round_idx == 4:
            champion = winners[0] if winners else ""
            break
        next_round = [(winners[i], winners[i + 1]) for i in range(0, len(winners) - 1, 2)]
        current_round = next_round

    return TournamentTrace(group_games=group_games, rounds=rounds, champion=champion)
