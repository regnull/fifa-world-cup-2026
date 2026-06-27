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
