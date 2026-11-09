"""Integration: competing duplicate-route alternatives and independent quota."""
from __future__ import annotations

from types import SimpleNamespace

import fleet
from fleet import RouteCandidate
from gamemode import EASY
from route_registry import RouteRegistry, endpoint


class Config:
    def get_bool(self, section, key, default=False):
        if key in ("allow_duplicate_routes", "auto_route", "autobuy_aircraft", "auto_seats"):
            return False
        if key == "analyze_duplicate_routes":
            return True
        return default

    def get_int(self, section, key, default=0):
        return {
            "route_analysis_per_cycle": 5,
            "fleet_actions_per_cycle": 2,
            "route_max_distance_big": 6000,
            "route_min_runway": 5000,
            "route_min_profit_gain_pct": 5,
        }.get(key, default)


def test_management_uses_five_analyses_without_consuming_two_real_actions(
    tmp_path, monkeypatch,
):
    registry = RouteRegistry(tmp_path / "routes.json")
    monkeypatch.setattr(fleet, "RouteRegistry", lambda: registry)
    monkeypatch.setattr(fleet, "measure_load", lambda bot: None)
    monkeypatch.setattr(fleet, "audit_routes", lambda bot, reg: None)
    observed = []
    monkeypatch.setattr(
        fleet, "resolve_duplicate_routes",
        lambda bot, reg, budget: observed.append(("analysis", budget)) or 0,
    )
    monkeypatch.setattr(fleet, "create_routes",
                        lambda *a: observed.append(("create", a[1])) or 0)

    class Bot:
        config = Config()
        stopping = False

        def open_popup(self, *args):
            pass

        def js(self, script):
            if script == "return $('#hParked').text();":
                return "1"
            if script == "return $('#hPending').text();":
                return "0"
            raise AssertionError(script)

        def update_stats(self, **kwargs):
            pass

        def close_popup(self):
            pass

    fleet.manage_fleet(Bot())
    assert observed == [("analysis", 5)]


def test_duplicate_planner_does_not_recommend_same_destination_twice(
    tmp_path, monkeypatch,
):
    registry = RouteRegistry(tmp_path / "registry.json")
    for id_, reg, origin, dest in [
        ("101", "DAC-1", "DAC", "OSL"), ("102", "DAC-2", "OSL", "DAC"),
        ("201", "DAC-3", "DAC", "DTW"), ("202", "DAC-4", "DTW", "DAC"),
    ]:
        registry.record(id_, reg, "A320", endpoint(code=origin), endpoint(code=dest),
                        source="game", at_base=True)
    assert registry.snapshot()["duplicate_routes"] == 2
    monkeypatch.setattr(fleet, "load_market", lambda: [])
    monkeypatch.setattr(
        fleet, "find_model",
        lambda *args: {"speed": 800, "fuel": 7, "capacity": 180, "range": 6000},
    )

    def fake_search(*args):
        return [
            RouteCandidate("1709", "Kinshasa (FIH)", 1700, 2000, 100, 0, 10000, "FIH"),
            RouteCandidate("451", "Addis Ababa (ADD)", 1500, 1800, 100, 0, 10000, "ADD"),
        ]

    monkeypatch.setattr(fleet, "search_routes", fake_search)
    monkeypatch.setattr(
        fleet, "rank_candidates",
        lambda choices, **kwargs: [
            (candidate, SimpleNamespace(
                profit_per_day=200 if candidate.code == "FIH" else 100,
            )) for candidate in choices
        ],
    )
    monkeypatch.setattr(
        fleet, "check_existing_route",
        lambda *args: SimpleNamespace(
            route_confirmed=True, route_id="1", game_endpoints=("DAC", "OSL"),
            reason="rota_confirmada",
        ),
    )

    class Bot:
        config = Config()
        mode = EASY
        dry_run = True
        stopping = False

        def open_popup(self, *args):
            pass

        def ajax(self, *args):
            pass

        def js(self, script, *args):
            if "select.options" in script:
                return [{"id": "3499", "text": "Dhaka, Bangladesh"}]
            if "document.getElementById('hubSelect')" in script:
                return True
            raise AssertionError(script)

        def load_factor(self):
            return 0.8

        def fuel_cost_basis(self):
            return 650

        def co2_cost_basis(self):
            return 125

    assert fleet.resolve_duplicate_routes(Bot(), registry, 2) == 0
    proposals = [
        row["proposal"] for row in registry.snapshot()["relations"]
        if row.get("proposal") and row["aircraft_id"] in ("102", "202")
    ]
    assert len(proposals) == 2
    assert {p["destination_code"] for p in proposals} == {"FIH", "ADD"}
    assert {p["origin_code"] for p in proposals} == {"DAC"}
