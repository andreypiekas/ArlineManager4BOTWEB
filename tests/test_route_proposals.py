"""Do not propose the same alternative twice or reserve obsolete proposals."""
from __future__ import annotations

import time

from route_proposals import proposal_reservations, proposed_route, reserved_by_other
from route_registry import endpoint


def row(ident, original, proposal, *, when=None):
    source, destination = original
    return {
        "aircraft_id": str(ident),
        "route_key": f"code:{source} ↔ code:{destination}",
        "proposal": {
            "origin_code": "LAX",
            "origin_id": "1440",
            "destination_code": "FIH",
            "destination_id": "",
            "current_route": f"code:{source} ↔ code:{destination}",
            "calculated_at": time.time() if when is None else when,
            "profit_per_day": 100_000,
            **proposal,
        },
    }


def test_same_proposed_pair_reserved_for_only_one_aircraft():
    now = time.time()
    a = row("101", ("LAX", "PBM"), {}, when=now - 100)
    b = row("102", ("LAX", "RUN"), {}, when=now - 50)
    reservations, conflicts = proposal_reservations([b, a], now=now)
    assert len(reservations) == 1
    assert reservations[0][0] == "101"
    assert conflicts == 1
    requested = proposed_route(b["proposal"])
    assert reserved_by_other(reservations, "102", requested)
    assert not reserved_by_other(reservations, "101", requested)


def test_outdated_proposals_and_changed_routes_are_not_reserved():
    now = time.time()
    expired = row("101", ("LAX", "PBM"), {}, when=now - 7 * 3600)
    moved = row("102", ("LAX", "RUN"), {}, when=now - 100)
    moved["route_key"] = "code:GRU ↔ code:LAX"
    future = row("103", ("LAX", "OSL"), {}, when=now + 100)
    reserved, conflicts = proposal_reservations([expired, moved, future], now=now)
    assert reserved == []
    assert conflicts == 0


def test_legacy_proposals_without_time_dont_block_forever():
    candidate = row("101", ("LAX", "PBM"), {})
    candidate["proposal"].pop("calculated_at")
    assert proposal_reservations([candidate])[0] == []


def test_icao_alias_can_be_detected_as_same_route():
    now = time.time()
    original = row("101", ("LAX", "RUN"), {}, when=now - 20)
    incoming = proposed_route({
        "origin_id": "1440", "destination_code": "FIH",
    })
    reservations, conflicts = proposal_reservations([original], now=now)
    assert conflicts == 0
    assert reserved_by_other(reservations, "102", incoming)


def test_invalid_or_same_airport_proposals_are_not_routes():
    assert proposed_route({}) is None
    assert proposed_route({"origin_code": "LAX", "destination_code": "LAX"}) is None
    assert proposed_route({"origin_code": "LAX", "destination_code": "12345"}) is None
    assert endpoint(code="LAX")["code"] == "LAX"
