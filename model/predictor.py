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
        # Orient odds to this matchup — the MatchOdds may have been looked up
        # from the reversed fixture (home/away swapped).
        if odds.home == away and odds.away == home:
            oh, oa = odds.odds_away, odds.odds_home
        else:
            oh, oa = odds.odds_home, odds.odds_away
        p_win, p_draw, p_loss = odds_to_probs(oh, odds.odds_draw, oa)
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
