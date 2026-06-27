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
