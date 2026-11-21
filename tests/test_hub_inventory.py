"""Roadmap Hubs: regression tests for game evidence and conservative aggregation."""
import json

from hub_inventory import HubInventory


def _hubs():
    return [
        {"id": "", "text": "Escolha uma base"},
        {"id": "101", "text": "São Paulo", "code": "GRU"},
        {"id": "202", "text": "Detroit", "code": "DTW"},
    ]


def test_waits_for_verified_hubs_and_does_not_erase_good_cache(tmp_path):
    inv = HubInventory(tmp_path / "hub_inventory.json")
    assert inv.snapshot(now=1000)["total_hubs"] == 0
    assert not inv.record_options([])
    assert inv.record_options(_hubs(), at=1000)
    assert not inv.record_options([{"id": "101", "text": "São Paulo"},
                                   {"id": "101", "text": "Duplicado"}], at=1001)
    assert not inv.record_options([{"id": "abc", "text": "A"}], at=1001)
    snap = HubInventory(inv.path).snapshot(now=1010)
    assert snap["total_hubs"] == 2
    assert [h["id"] for h in snap["hubs"]] == ["101", "202"]
    assert snap["source"] == "game_research_hub_select"
    assert json.loads(inv.path.read_text(encoding="utf-8"))["read_at"] == 1000


def test_route_endpoints_and_at_base_never_assign_an_aircraft(tmp_path):
    inv = HubInventory(tmp_path / "hub_inventory.json")
    assert inv.record_options(_hubs(), at=1000)
    report = {"relations": [
        {"aircraft_id": "a1", "registration": "PP-1", "at_base": True,
         "origin": {"id": "101"}, "destination": {"id": "202"}, "profit_per_day": 500},
        {"aircraft_id": "a2", "registration": "PP-2", "home_base_id": "101",
         "home_base_source": "registro_manual", "home_base_verified_at": 900},
        {"aircraft_id": "a3", "registration": "PP-3", "home_base_id": "999",
         "home_base_source": "game", "home_base_verified_at": 900},
    ]}
    snap = inv.snapshot(report, now=1100)
    assert [h["confirmed_aircraft"] for h in snap["hubs"]] == [0, 0]
    assert all(h["profit_per_day"] is None for h in snap["hubs"])
    assert {a["aircraft_id"] for a in snap["unconfirmed_aircraft"]} == {"a1", "a2", "a3"}


def test_unique_game_id_and_profit_only_for_matching_recent_route(tmp_path):
    inv = HubInventory(tmp_path / "hub_inventory.json")
    inv.record_options(_hubs(), at=1000)
    rows = [
        {"aircraft_id": "1", "registration": "OLD", "home_base_id": "101",
         "home_base_source": "game", "home_base_verified_at": 1000,
         "route_key": "A <-> B", "profit_route_key": "A <-> B",
         "profit_calculated_at": 1000, "profit_per_day": 250},
        {"aircraft_id": "1", "registration": "NEW", "home_base_id": "202",
         "home_base_source": "game", "home_base_verified_at": 1000},
        {"aircraft_id": "2", "home_base_id": "101", "home_base_source": "game",
         "home_base_verified_at": 1000,
         "route_key": "B <-> C", "profit_route_key": "A <-> B",
         "profit_calculated_at": 1000, "profit_per_day": 999},
        {"aircraft_id": "3", "home_base_id": "202", "home_base_source": "game",
         "home_base_verified_at": 1000,
         "route_key": "D <-> E", "profit_route_key": "D <-> E",
         "profit_calculated_at": 1000, "profit_per_day": -15},
    ]
    snap = inv.snapshot({"relations": rows}, now=1100)
    a, b = snap["hubs"]
    assert a["confirmed_aircraft"] == 2
    assert b["confirmed_aircraft"] == 1
    assert a["profit_per_day"] == 250
    assert a["profit_coverage"] == 1
    assert b["profit_per_day"] == -15
    assert b["profit_coverage"] == 1
    assert a["aircraft"][0]["registration"] == "OLD"


def test_stale_readings_are_labeled_and_estimates_expire(tmp_path):
    inv = HubInventory(tmp_path / "hub_inventory.json")
    inv.record_options(_hubs(), at=100)
    report = {"relations": [{
        "aircraft_id": "x", "home_base_id": "101", "home_base_source": "game",
        "home_base_verified_at": 100, "route_key": "A",
        "profit_route_key": "A", "profit_per_day": 10, "profit_calculated_at": 100,
    }]}
    snap = inv.snapshot(report, now=8 * 86400)
    assert snap["stale"] is True
    assert snap["total_hubs"] == 2
    assert snap["hubs"][0]["profit_per_day"] is None
    assert snap["hubs"][0]["profit_coverage"] == 0


def test_profile_path_is_resolved_lazily(monkeypatch, tmp_path):
    import hub_inventory
    from types import SimpleNamespace

    one = tmp_path / "profile_a"
    two = tmp_path / "profile_b"
    monkeypatch.setattr(hub_inventory.paths, "current", lambda: SimpleNamespace(data=one))
    assert HubInventory().record_options(_hubs(), at=1000)
    monkeypatch.setattr(hub_inventory.paths, "current", lambda: SimpleNamespace(data=two))
    assert HubInventory().snapshot(now=1000)["total_hubs"] == 0
