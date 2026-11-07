"""Estimate route-level operating profit before opening an AM4 route.

The formulas and class-capacity model are informed by the MIT-licensed community
research at https://github.com/abc8747/am4 (Copyright 2023 Abraham Cheung).
This is an independent Python approximation for the data our game UI exposes.
The game's own route form remains authoritative for final prices and fees.

Important limitations:
* Market records do not contain an aircraft's current seat distribution, CO2
  coefficient, Cost Index, training levels, or A-check cost.
* Premium allocation is hypothetical when automatic seat management is on.
* Distances shown in the game's research table are approximate.
Consequently these numbers rank candidates, not guarantee their actual income.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite
from typing import Optional

from gamemode import GameMode

TURNAROUND_H = 0.1  # six minutes per one-way leg, matching existing project assumptions
ENGINE_FUEL = 0.94  # observed approximation; not a substitute for training/CI data
CO2_PER_PAX_KM = 0.18  # fallback estimate while the game does not expose per-aircraft CO2
CLASS_WEIGHTS = (1, 2, 3)


@dataclass(frozen=True)
class RouteEconomics:
    profit_per_day: float
    revenue_per_day: float
    fuel_cost_per_day: float
    co2_cost_per_day: float
    legs_per_day: float
    layout: tuple[int, int, int]
    passengers_per_day: tuple[float, float, float]


def _suggest_layout(capacity: int, demands: tuple[int, int, int],
                    legs: float, load: float, premium: bool) -> tuple[int, int, int]:
    """Allocate capacity by F, J, then Y, using class demand per departure.

    This is only a financial what-if, not a command to reconfigure seats.
    Most routes below 6,000 km benefit from this ordering (abc8747/am4).
    """
    if not premium:
        return capacity, 0, 0
    allocated = [0, 0, 0]
    remaining = capacity
    for cls in (2, 1, 0):
        units = CLASS_WEIGHTS[cls]
        necessary = ceil(demands[cls] / max(legs * load, 0.01))
        count = min(remaining // units, max(0, necessary))
        allocated[cls] = count
        remaining -= count * units
    return tuple(allocated)


def estimate_route(candidate, *, seats: int, model: Optional[dict],
                   mode: GameMode, load_factor: float,
                   fuel_price: float, co2_price: float,
                   premium: bool) -> Optional[RouteEconomics]:
    """Rank routes with demand-limited Y/J/F sales minus fuel and CO2 costs.

    Return None when model data is missing, allowing the original demand sorter
    to remain the fallback instead of inventing speeds or fuel consumption.
    """
    if not model:
        return None
    try:
        distance = float(candidate.distance)
        speed = float(model.get("speed") or 0)
        fuel_rate = float(model.get("fuel") or 0)
        actual_seats = int(seats)
        capacity = int(model.get("capacity") or 0) if premium else actual_seats
        if capacity <= 0:
            capacity = actual_seats
        load = max(0.1, min(1.0, float(load_factor)))
        price_fuel, price_co2 = float(fuel_price), float(co2_price)
    except (TypeError, ValueError, OverflowError):
        return None
    if not all(map(isfinite, (distance, speed, fuel_rate, load, price_fuel, price_co2))):
        return None
    if distance < 100 or speed <= 0 or fuel_rate <= 0 or capacity <= 0 or price_fuel < 0 or price_co2 < 0:
        return None

    legs = 24 / (distance / (speed * mode.speed) + TURNAROUND_H)
    demand = (max(0, int(candidate.y)), max(0, int(candidate.j)), max(0, int(candidate.f)))
    layout = _suggest_layout(capacity, demand, legs, load, premium)
    sold = tuple(min(demand[i], layout[i] * load * legs) for i in range(3))
    # The current game UI uses its own autoprice (not the higher optimal-price
    # multipliers). Estimating higher prices before setting them would misrank.
    revenue = sum(sold[i] * mode.fare(i, distance) for i in range(3))
    fuel = legs * fuel_rate * ENGINE_FUEL * distance * price_fuel / 1000
    co2 = sum(sold[i] * CLASS_WEIGHTS[i] for i in range(3)) * CO2_PER_PAX_KM * distance * price_co2 / 1000
    return RouteEconomics(revenue - fuel - co2, revenue, fuel, co2, legs, layout, sold)


def rank_candidates(candidates, **estimate_kwargs):
    """Return (candidate, estimate) best-first; fall back to demand when data is missing."""
    ranked = [(candidate, estimate_route(candidate, **estimate_kwargs)) for candidate in candidates]
    if any(result is not None for _, result in ranked):
        ranked.sort(
            key=lambda item: (
                item[1] is not None,
                item[1].profit_per_day if item[1] is not None else float("-inf"),
                item[0].y + (2 * item[0].j + 3 * item[0].f if estimate_kwargs["premium"] else 0),
            ),
            reverse=True,
        )
    else:
        ranked.sort(
            key=lambda item: item[0].y + (
                2 * item[0].j + 3 * item[0].f if estimate_kwargs["premium"] else 0
            ),
            reverse=True,
        )
    return ranked
