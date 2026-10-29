"""Tie model probabilities to real-world rates.

The judging model decides who is more or less likely to act (order); benchmarks fix
how many do (level): p' = sigma(logit(p) + b), with one b per decision shared by
every plan, so calibration never erases a difference between plans.
"""

import math

EPS = 1e-6


def logit(p):
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def sigma(x):
    return 1 / (1 + math.exp(-x))


def shift(p, b):
    return sigma(logit(p) + b)


def shift_options(probs, shifts, residual):
    """Shift some options of a categorical answer in logit space; `residual` absorbs the change.

    Shifting options independently (instead of rescaling all the others) keeps one
    calibration target from leaking into another, e.g. fewer deletes must not mean more payments.
    """
    out = dict(probs)
    for option, b in shifts.items():
        out[option] = shift(probs[option], b)
    fixed = sum(v for k, v in out.items() if k != residual)
    if fixed > 1:
        out = {k: (v / fixed if k != residual else 0.0) for k, v in out.items()}
    else:
        out[residual] = 1 - fixed
    return out


def fit_shifts(measure, targets, iters=12, damping=0.6, limit=4.0, shifts=None):
    """Damped fixed-point fit of one logit shift per target.

    measure(shifts) -> {name: observed rate}; each round moves b by part of the logit gap,
    within +-limit. Returns (shifts, last observed rates).
    """
    shifts = dict(shifts or {k: 0.0 for k in targets})
    for _ in range(iters):
        seen = measure(shifts)
        for k, target in targets.items():
            if seen.get(k) is not None:
                b = shifts[k] + damping * (logit(target) - logit(seen[k]))
                shifts[k] = max(-limit, min(limit, b))
    return shifts, measure(shifts)
