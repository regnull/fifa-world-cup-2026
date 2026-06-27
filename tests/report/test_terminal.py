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
