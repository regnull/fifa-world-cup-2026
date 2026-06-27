import math
import numpy as np

# Lookup: p_win → (lambda_winner, lambda_loser)
# Calibrated to historical World Cup goal data
_LAMBDA_TABLE = [
    (0.80, 2.10, 0.70),
    (0.65, 1.80, 0.90),
    (0.50, 1.50, 1.10),
    (0.40, 1.25, 1.25),
    (0.25, 0.90, 1.80),
    (0.00, 0.70, 2.10),
]

# Draw base goal-rate (used for D bucket)
_DRAW_LAMBDA = 1.1


def _get_lambdas(p_win: float) -> tuple[float, float]:
    """Return (lambda_winner, lambda_loser) for a given win probability."""
    for threshold, lw, ll in _LAMBDA_TABLE:
        if p_win >= threshold:
            return lw, ll
    return 0.70, 2.10


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _p_home_wins(lh: float, la: float, max_goals: int = 20) -> float:
    """P(h > a) when h ~ Poisson(lh), a ~ Poisson(la)."""
    return sum(
        _poisson_pmf(h, lh) * _poisson_pmf(a, la)
        for h in range(1, max_goals)
        for a in range(h)
    )


def sample_score(
    p_win: float, p_draw: float, p_loss: float, knockout: bool = False
) -> tuple[int, int]:
    """
    Sample (home_goals, away_goals) consistent with the given probabilities.

    Uses rejection sampling within each outcome bucket (W/D/L), with bucket
    selection probabilities adjusted to compensate for per-bucket acceptance
    rates so that the marginal distribution matches (p_win, p_draw, p_loss).

    In knockout mode, draws are resolved: the draw probability is split equally
    between W and L before adjustment.
    """
    rng = np.random.default_rng()

    if knockout:
        p_win_eff = p_win + p_draw / 2.0
        p_loss_eff = p_loss + p_draw / 2.0
        p_draw_eff = 0.0
    else:
        p_win_eff, p_draw_eff, p_loss_eff = p_win, p_draw, p_loss

    # Lambda pairs for each bucket
    lw_w, ll_w = _get_lambdas(p_win)   # W bucket: h ~ lw_w, a ~ ll_w
    lw_l, ll_l = _get_lambdas(p_loss)  # L bucket: h ~ ll_l, a ~ lw_l

    # Acceptance rates per bucket
    acc_w = _p_home_wins(lw_w, ll_w) if p_win_eff > 0 else 1.0
    acc_l = _p_home_wins(lw_l, ll_l) if p_loss_eff > 0 else 1.0  # = P(a>h) by symmetry
    acc_d = 1.0  # draw bucket always accepted

    # Adjusted raw weights so marginal rates match desired probabilities
    raw_w = p_win_eff / acc_w if p_win_eff > 0 else 0.0
    raw_d = p_draw_eff / acc_d if p_draw_eff > 0 else 0.0
    raw_l = p_loss_eff / acc_l if p_loss_eff > 0 else 0.0
    total = raw_w + raw_d + raw_l

    adj_w, adj_d, adj_l = raw_w / total, raw_d / total, raw_l / total

    while True:
        bucket = rng.choice(["W", "D", "L"], p=[adj_w, adj_d, adj_l])

        if bucket == "W":
            h = int(rng.poisson(lw_w))
            a = int(rng.poisson(ll_w))
            if h > a:
                return h, a

        elif bucket == "D":
            base = int(rng.poisson(_DRAW_LAMBDA))
            return base, base

        else:  # "L"
            # h ~ ll_l, a ~ lw_l  →  condition: a > h
            h = int(rng.poisson(ll_l))
            a = int(rng.poisson(lw_l))
            if a > h:
                return h, a
