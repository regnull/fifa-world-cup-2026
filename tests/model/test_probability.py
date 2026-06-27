import math
from model.probability import odds_to_probs, elo_to_probs


def test_odds_to_probs_sum_to_one():
    p1, px, p2 = odds_to_probs(2.5, 3.2, 2.8)
    assert abs(p1 + px + p2 - 1.0) < 1e-9


def test_odds_to_probs_removes_vig():
    # Equal odds — should give equal probabilities
    p1, px, p2 = odds_to_probs(3.0, 3.0, 3.0)
    assert abs(p1 - 1/3) < 0.01
    assert abs(px - 1/3) < 0.01
    assert abs(p2 - 1/3) < 0.01


def test_odds_to_probs_favourite_has_higher_prob():
    p1, px, p2 = odds_to_probs(1.5, 4.0, 6.0)
    assert p1 > px > p2


def test_elo_to_probs_sum_to_one():
    p1, px, p2 = elo_to_probs(2000.0, 2000.0)
    assert abs(p1 + px + p2 - 1.0) < 1e-9


def test_elo_to_probs_equal_teams():
    p1, px, p2 = elo_to_probs(2000.0, 2000.0)
    # Equal teams → home win prob ≈ away win prob, both < 0.5
    assert abs(p1 - p2) < 0.02
    assert px > 0.15   # draws are common at equal strength


def test_elo_to_probs_strong_favourite():
    p1, px, p2 = elo_to_probs(2200.0, 1800.0)
    assert p1 > 0.7   # strong favourite should win >70%


def test_elo_to_probs_all_positive():
    p1, px, p2 = elo_to_probs(2100.0, 1900.0)
    assert p1 > 0
    assert px > 0
    assert p2 > 0
