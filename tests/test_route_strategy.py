"""Pure guardrails: losing routes are not opened, and reroutes must improve known profit."""
from dataclasses import dataclass
from types import SimpleNamespace

from route_strategy import best_reroute, improvement_threshold, profitable_candidates


@dataclass(frozen=True)
class Candidate:
    code: str


def econ(value):
    return SimpleNamespace(profit_per_day=value)


def test_creation_never_selects_known_loss_when_one_candidate_is_profitable():
    loss, winner, unknown = Candidate("LOSS"), Candidate("WIN"), Candidate("UNKNOWN")
    ranked = [(loss, econ(-50)), (unknown, None), (winner, econ(70))]
    assert profitable_candidates(ranked) == [(winner, ranked[2][1])]


def test_all_unprofitable_candidates_cannot_trigger_new_route():
    ranked = [(Candidate("X"), econ(-1)), (Candidate("Y"), econ(0))]
    assert profitable_candidates(ranked) == []


def test_demand_fallback_remains_when_market_has_no_valid_estimate():
    ranked = [(Candidate("A"), None), (Candidate("B"), None)]
    assert profitable_candidates(ranked) == ranked


def test_failed_or_nonfinite_model_predictions_must_not_fallback_to_demand():
    assert profitable_candidates([(Candidate("BAD"), econ(float("nan")))]) == []
    assert profitable_candidates([(Candidate("BAD"), econ(float("inf")))]) == []


def test_reroute_must_improve_known_current_profit_by_minimum_margin():
    more, less = Candidate("MORE"), Candidate("LESS")
    ranked = [(less, econ(104)), (more, econ(106))]
    best, threshold = best_reroute(ranked, current_profit=100, minimum_gain_percent=5)
    assert threshold == 105
    assert best[0] is more
    assert best[1].profit_per_day == 106


def test_reroute_rejects_alternative_with_no_material_gain():
    ranked = [(Candidate("WORSE"), econ(90)), (Candidate("MARGINAL"), econ(102))]
    best, threshold = best_reroute(ranked, current_profit=100, minimum_gain_percent=5)
    assert best is None
    assert threshold == 105


def test_unknown_baseline_means_positive_estimate_only():
    best, threshold = best_reroute(
        [(Candidate("LOSS"), econ(-20)), (Candidate("GAIN"), econ(35))],
        current_profit=None,
    )
    assert threshold is None
    assert best[0].code == "GAIN"
    assert improvement_threshold(float("nan")) is None
    assert improvement_threshold(0) is None
    assert improvement_threshold(True) is None


def test_percent_gain_is_clamped_to_avoid_nonsensical_settings():
    assert improvement_threshold(100, -5) == 100
    assert improvement_threshold(100, 500) == 200
