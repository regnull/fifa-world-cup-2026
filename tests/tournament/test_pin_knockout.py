from scrape.models import KnockoutResult
from tournament.simulator import resolve_knockout_game


def test_pinned_game_is_deterministic():
    results = {
        frozenset({"Brazil", "Japan"}): KnockoutResult(
            home="Brazil", away="Japan", home_goals=2, away_goals=1, winner="Brazil"
        )
    }
    # Orientation in the bracket may differ from the scraped orientation.
    for home, away in [("Brazil", "Japan"), ("Japan", "Brazil")]:
        r = resolve_knockout_game(home, away, {}, {}, results)
        assert r.winner == "Brazil"
        assert r.method == "final"
        # Score is reported relative to the bracket's home/away orientation.
        if home == "Brazil":
            assert (r.home_goals, r.away_goals) == (2, 1)
        else:
            assert (r.home_goals, r.away_goals) == (1, 2)


def test_unpinned_game_falls_back_to_prediction():
    r = resolve_knockout_game("Spain", "Austria", {}, {"Spain": 2000, "Austria": 1500}, {})
    assert r.winner in {"Spain", "Austria"}
    assert r.method != "final"
