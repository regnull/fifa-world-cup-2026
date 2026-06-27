

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
