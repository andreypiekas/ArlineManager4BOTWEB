"""Conservative reservations for alternative routes proposed by the read-only planner.

Proposals aren't active routes, but two aircraft receiving the *same*
replacement would immediately recreate a duplicate if ever executed.
The planner therefore reserves one proposed airport pair per aircraft.
Reservations are bounded in time and tied to the current verified route.
"""
from __future__ import annotations

import time
from typing import Optional

from airport_catalog import by_code, game_code
from route_registry import endpoint, same_route

PROPOSAL_TTL_SECONDS = 6 * 3600


def proposed_route(proposal: dict) -> Optional[dict]:
    """Normalize game IDs, IATA and ICAO using the existing airport catalog."""
    if not isinstance(proposal, dict):
        return None
    endpoints = []
    for side in ("origin", "destination"):
        ident = proposal.get(f"{side}_id")
        code = game_code(ident, proposal.get(f"{side}_code"))
        item = by_code(code)
        if item is not None:
            code = item.iata
        place = endpoint(ident, code=code)
        if not (place.get("id") or place.get("code")):
            return None
        endpoints.append(place)
    if same_route(
        {"origin": endpoints[0], "destination": endpoints[1]},
        {"origin": endpoints[0], "destination": endpoints[0]},
    ):
        return None
    return {"origin": endpoints[0], "destination": endpoints[1]}


def proposal_reservations(rows: list[dict], *, now: Optional[float] = None,
                          max_age_seconds: int = PROPOSAL_TTL_SECONDS,
                          ) -> tuple[list[tuple[str, dict]], int]:
    """Keep the oldest current proposal for each pair; report conflicts.

    A stale proposal or a proposal for a *previous* assignment does not
    reserve a route. Legacy records without calculated_at are intentionally
    excluded, so no old data blocks planning permanently.
    """
    current_time = time.time() if now is None else now
    eligible = []
    for row in rows:
        proposal = row.get("proposal") or {}
        timestamp = proposal.get("calculated_at")
        if not isinstance(timestamp, (float, int)):
            continue
        age = current_time - timestamp
        if age < 0 or age >= max_age_seconds:
            continue
        if proposal.get("current_route") != row.get("route_key"):
            continue
        route = proposed_route(proposal)
        if not route:
            continue
        eligible.append((timestamp, str(row.get("aircraft_id") or ""), route))
    eligible.sort(key=lambda item: (item[0], item[1]))
    reservations: list[tuple[str, dict]] = []
    conflicts = 0
    for _, aircraft_id, route in eligible:
        if any(same_route(route, existing) for _, existing in reservations):
            conflicts += 1
            continue
        reservations.append((aircraft_id, route))
    return reservations, conflicts


def reserved_by_other(reservations: list[tuple[str, dict]],
                      aircraft_id: str, desired: dict) -> bool:
    """Do not suggest a route already proposed for a different aircraft."""
    return any(owner != str(aircraft_id) and same_route(route, desired)
               for owner, route in reservations)
