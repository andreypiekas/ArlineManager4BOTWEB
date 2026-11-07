"""Pure route-ranking tests; no browser, AM4 login or real purchases."""
from dataclasses import dataclass

from gamemode import EASY, REALISM
from route_optimizer import estimate_route


@dataclass
class Candidate:
    distance: int
    y: int
    j: int = 0
    f: int = 0


MODEL = {"speed": 800, "fuel": 7, "capacity": 180}


def estimate(route, **kw):
    return estimate_route(
        route, seats=180, model=MODEL, mode=EASY,
        load_factor=0.8, fuel_price=650, co2_price=125,
        premium=False, **kw,
    )


def test_profit_can_beat_greater_demand():
    busy_short = estimate(Candidate(600, 1800))
    profitable_long = estimate(Candidate(2200, 1200))
    assert profitable_long.profit_per_day > busy_short.profit_per_day
    assert profitable_long.revenue_per_day > 0
    assert profitable_long.fuel_cost_per_day > 0


def test_demand_cannot_be_sold_more_than_once_per_day():
    route = estimate(Candidate(1200, 90))
    assert route.passengers_per_day[0] == 90.0
    assert route.layout == (180, 0, 0)


def test_premium_uses_class_specific_fares_and_capacity_units():
    route = Candidate(2200, 100, 550, 550)
    result = estimate_route(
        route, seats=180, model=MODEL, mode=EASY,
        load_factor=0.8, fuel_price=650, co2_price=125, premium=True,
    )
    assert result.layout[2] > 0
    assert result.layout[0] + 2 * result.layout[1] + 3 * result.layout[2] <= MODEL["capacity"]
    assert result.passengers_per_day[2] <= route.f
    assert result.revenue_per_day > 0


def test_missing_model_preserves_demand_only_fallback():
    result = estimate_route(
        Candidate(1200, 900), seats=180, model=None,
        mode=EASY, load_factor=0.8, fuel_price=650,
        co2_price=125, premium=False,
    )
    assert result is None


def test_invalid_model_does_not_generate_fake_profit():
    result = estimate_route(
        Candidate(1200, 900), seats=180,
        model={"speed": 800, "fuel": 0, "capacity": 180},
        mode=EASY, load_factor=0.8, fuel_price=650,
        co2_price=125, premium=False,
    )
    assert result is None


def test_realistic_mode_changes_expected_revenue_and_flights():
    r = Candidate(2000, 5000)
    easy = estimate_route(
        r, seats=180, model=MODEL, mode=EASY,
        load_factor=0.8, fuel_price=650, co2_price=125, premium=False,
    )
    realism = estimate_route(
        r, seats=180, model=MODEL, mode=REALISM,
        load_factor=0.8, fuel_price=650, co2_price=125, premium=False,
    )
    assert easy.legs_per_day > realism.legs_per_day
    assert easy.revenue_per_day > realism.revenue_per_day


def test_profit_ranking_prefers_longer_but_more_profitable_route():
    from route_optimizer import rank_candidates
    short = Candidate(600, 1800)
    long = Candidate(2200, 1200)
    ranked = rank_candidates(
        [short, long], seats=180, model=MODEL, mode=EASY,
        load_factor=0.8, fuel_price=650, co2_price=125, premium=False,
    )
    assert ranked[0][0] is long
    assert ranked[0][1].profit_per_day > ranked[1][1].profit_per_day


def test_fallback_ranking_prefers_demand_with_missing_model():
    from route_optimizer import rank_candidates
    less = Candidate(1000, 1200)
    more = Candidate(1000, 1500)
    ranked = rank_candidates(
        [less, more], seats=180, model=None, mode=EASY,
        load_factor=0.8, fuel_price=650, co2_price=125, premium=False,
    )
    assert ranked[0][0] is more
    assert all(estimate is None for _, estimate in ranked)


def test_seat_class_demand_is_not_double_counted():
    from route_optimizer import rank_candidates
    first = Candidate(2000, 50, 0, 350)
    second = Candidate(2000, 600, 0, 0)
    ranked = rank_candidates(
        [first, second], seats=180, model=None, mode=EASY,
        load_factor=0.8, fuel_price=650, co2_price=125, premium=True,
    )
    assert ranked[0][0] is first
