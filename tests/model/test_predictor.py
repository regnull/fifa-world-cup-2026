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


def test_predict_orients_reversed_odds():
    """Odds looked up from the reversed fixture must be re-oriented.

    ESPN stores the fixture as Panama (home) vs England (away): Panama the
    underdog at 17.0, England the favourite at 1.15. When we predict
    "England vs Panama" (England as home), England must inherit the 1.15
    favourite odds — not Panama's 17.0 home odds.
    """
    odds = MatchOdds(home="Panama", away="England",
                     odds_home=17.0, odds_draw=9.0, odds_away=1.15)
    wins = sum(
        1 for _ in range(2000)
        if predict("England", "Panama", odds=odds,
                   elo_map={"England": 2028.0, "Panama": 1668.0}).winner == "England"
    )
    assert wins / 2000 > 0.60, f"Expected >60% England wins, got {wins/2000:.2f}"
