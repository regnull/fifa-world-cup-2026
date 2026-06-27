import numpy as np
from model.poisson import sample_score


def test_sample_score_respects_winner_distribution():
    """Over many samples, winner frequency should match win probabilities."""
    n = 10_000
    p_win, p_draw, p_loss = 0.60, 0.20, 0.20
    wins = draws = losses = 0
    for _ in range(n):
        h, a = sample_score(p_win, p_draw, p_loss, knockout=False)
        if h > a:
            wins += 1
        elif h == a:
            draws += 1
        else:
            losses += 1
    assert abs(wins / n - p_win) < 0.03, f"win rate {wins/n:.3f} expected ~{p_win}"
    assert abs(draws / n - p_draw) < 0.03
    assert abs(losses / n - p_loss) < 0.03


def test_sample_score_knockout_no_draw():
    """In knockout mode, scores must never be a draw."""
    for _ in range(200):
        h, a = sample_score(0.50, 0.20, 0.30, knockout=True)
        assert h != a, "Knockout match ended in draw"


def test_sample_score_returns_non_negative():
    for _ in range(100):
        h, a = sample_score(0.6, 0.2, 0.2)
        assert h >= 0
        assert a >= 0
