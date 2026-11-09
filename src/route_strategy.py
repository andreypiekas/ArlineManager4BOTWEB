"""Pure policies for profitable route creation and non-destructive reroute proposals.

The game's live research/search and purchase forms are authoritative. These
helpers only filter and rank local calculations, never send game commands.
"""
from __future__ import annotations

from math import isfinite
from typing import Iterable, Optional, TypeVar

Candidate = TypeVar("Candidate")


def profitable_candidates(ranked: Iterable[tuple[Candidate, object]],
                          *, minimum_daily_profit: float = 0.0
                          ) -> list[tuple[Candidate, object]]:
    """Never propose a known-loss route as profitable.

    If NO estimate is available, preserve the pre-existing demand-based
    fallback; if any valid estimate exists, reject unknown and losing routes.
    """
    choices = list(ranked)
    evaluated = [
        (candidate, estimate) for candidate, estimate in choices
        if estimate is not None and isinstance(getattr(estimate, "profit_per_day", None), (int, float))
        and isfinite(float(estimate.profit_per_day))
    ]
    if not evaluated:
        # None means there was no model for a reliable profit estimate.
        # If a model produced NaN/infinity instead, fail closed.
        return choices if all(est is None for _, est in choices) else []
    return [
        (candidate, estimate) for candidate, estimate in evaluated
        if float(estimate.profit_per_day) > max(0, minimum_daily_profit)
    ]


def improvement_threshold(current_profit: object, minimum_gain_percent: int = 5
                          ) -> Optional[float]:
    """Return the minimum profitable alternative, or None if baseline unknown.

    A stored historical estimate is not verified real game profit. We use it
    to avoid proposing a clearly worse alternative, not to promise savings.
    """
    if isinstance(current_profit, bool) or not isinstance(current_profit, (int, float)):
        return None
    if not isfinite(float(current_profit)) or float(current_profit) <= 0:
        return None
    margin = max(0, min(100, int(minimum_gain_percent)))
    return float(current_profit) * (1 + margin / 100)


def best_reroute(ranked: Iterable[tuple[Candidate, object]], *,
                 current_profit: object = None, minimum_gain_percent: int = 5
                 ) -> tuple[Optional[tuple[Candidate, object]], Optional[float]]:
    """Pick the best positive alternative only when it beats a known baseline."""
    baseline = improvement_threshold(current_profit, minimum_gain_percent)
    for candidate, estimate in profitable_candidates(ranked):
        if estimate is None:
            continue
        if baseline is not None and estimate.profit_per_day <= baseline:
            continue
        return (candidate, estimate), baseline
    return None, baseline
