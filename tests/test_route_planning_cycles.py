"""Route optimization must remain read-only, profitable and fair across all duplicates."""
from __future__ import annotations

from types import SimpleNamespace

import fleet
from fleet import ParkedAircraft, RouteCandidate, create_routes, resolve_duplicate_routes
from gamemode import EASY
from route_registry import RouteRegistry, endpoint


class Config:
    def __init__(self, *, analyze=True):
        self.analyze = analyze

    def get_bool(self, section, name, default=False):
        if name == "analyze_duplicate_routes":
            return self.analyze
        if name == "auto_route":
            return False
        if name in ("auto_seats", "allow_duplicate_routes"):
            return False
        return default

    def get_int(self, section, name, default=0):
        if name == "fleet_actions_per_cycle":
            return 2
        if name == "route_min_profit_gain_pct":
            return 5
        return default


def registry_with_four_duplicates(tmp_path):
    registry = RouteRegistry(tmp_path / "registry.json")
    pairs = [("DAC", "OSL"), ("LAX", "PBM"), ("XAP", "GRU"), ("DTW", "TXL")]
    for idx, (dep, arr) in enumerate(pairs):
        registry.record(str(idx * 10 + 1), f"PP-{idx}-1", "A320",
                        endpoint(code=dep), endpoint(code=arr), source="game")
        registry.record(str(idx * 10 + 2), f"PP-{idx}-2", "A320",
                        endpoint(code=arr), endpoint(code=dep), source="game")
    return registry


def test_analysis_continues_with_automatic_route_creation_off_and_rotates(tmp_path, monkeypatch):
    registry = registry_with_four_duplicates(tmp_path)
    assert registry.snapshot()["duplicate_routes"] == 4
    monkeypatch.setattr(fleet, "load_market", lambda: [])
    monkeypatch.setattr(fleet, "find_model", lambda *args: None)

    class Bot:
        config = Config(analyze=True)
        stopping = False
        dry_run = True

        def open_popup(self, *args):
            raise AssertionError("No model => no live research needed")

    assert resolve_duplicate_routes(Bot(), registry, 2) == 0
    rows = registry.snapshot()["relations"]
    assert sum(bool(r.get("last_planned_at")) for r in rows) == 2
    assert sum(r.get("status") == "aguardando_dados_do_modelo" for r in rows) == 2
    assert sum(r.get("status") == "pendente_limite_ciclo" for r in rows) == 2
    # The previously deferred aircraft must be the next ones analyzed,
    # even though those that failed earlier never received proposals.
    assert resolve_duplicate_routes(Bot(), registry, 2) == 0
    rows = registry.snapshot()["relations"]
    assert sum(bool(r.get("last_planned_at")) for r in rows) == 4


def test_disabling_analysis_skips_game_research_and_preserves_proposal(tmp_path, monkeypatch):
    registry = registry_with_four_duplicates(tmp_path)
    snapshot = registry.snapshot()
    candidate_id = snapshot["duplicates"][0]["aircraft"][1]["id"]
    proposal = {"destination": "SIN", "profit_per_day": 100}
    registry.note(candidate_id, "simulacao_redirecionamento", proposal=proposal)
    monkeypatch.setattr(fleet, "load_market", lambda: [])

    class Bot:
        config = Config(analyze=False)
        stopping = False
        dry_run = True

        def open_popup(self, *args):
            raise AssertionError("Disabled planner must not read the game")

    assert resolve_duplicate_routes(Bot(), registry, 2) == 0
    record = next(r for r in registry.snapshot()["relations"] if r["aircraft_id"] == candidate_id)
    assert record["status"] == "aguardando_ativacao_de_analise"
    assert record["proposal"] == proposal


def test_creation_skips_known_unprofitable_routes_without_opening_order_form(tmp_path, monkeypatch):
    reg = RouteRegistry(tmp_path / "routes.json")
    monkeypatch.setattr(fleet, "RouteRegistry", lambda: reg)
    monkeypatch.setattr(fleet, "read_parked", lambda bot: [
        ParkedAircraft("101", "A320", "PP-101", 180),
    ])
    monkeypatch.setattr(fleet, "load_market", lambda: [])
    monkeypatch.setattr(fleet, "find_model", lambda *args: {
        "speed": 800, "fuel": 100000, "capacity": 180, "range": 6000,
    })
    monkeypatch.setattr(fleet, "search_routes", lambda *args: [
        RouteCandidate("645", "Oslo", 1000, 20, 0, 0, 10000, "OSL"),
    ])
    monkeypatch.setattr(
        fleet, "create_route",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Known loss must never open order form")
        ),
    )

    class Bot:
        config = Config()
        mode = EASY
        stopping = False
        dry_run = True

        def open_popup(self, *args):
            pass

        def ajax(self, *args):
            pass

        def js(self, script, *args):
            assert "hubSelect" in script
            return "2926"

        def load_factor(self):
            return 0.8

        def fuel_cost_basis(self):
            return 1000

        def co2_cost_basis(self):
            return 150

    assert create_routes(Bot(), 1) == 0


def test_same_destination_allowed_for_different_origins_when_duplicates_off(tmp_path, monkeypatch):
    reg = RouteRegistry(tmp_path / "routes.json")
    monkeypatch.setattr(fleet, "RouteRegistry", lambda: reg)
    monkeypatch.setattr(fleet, "read_parked", lambda bot: [
        ParkedAircraft("101", "A320", "PP-101", 180),
        ParkedAircraft("102", "A320", "PP-102", 180),
    ])
    monkeypatch.setattr(fleet, "load_market", lambda: [])
    monkeypatch.setattr(fleet, "find_model", lambda *args: None)
    monkeypatch.setattr(fleet, "search_routes", lambda *args: [
        RouteCandidate("645", "Oslo", 900, 1200, 0, 0, 10000, "OSL"),
    ])
    called = []

    def fake_create(bot, aircraft, candidate, **kwargs):
        called.append((kwargs["origin_id"], candidate.arr_id))
        return "dry"

    monkeypatch.setattr(fleet, "create_route", fake_create)

    class Bot:
        config = Config()
        mode = EASY
        stopping = False
        dry_run = True

        def __init__(self):
            self.research = 0

        def open_popup(self, *args):
            pass

        def ajax(self, url, target):
            if url == "research_main.php":
                self.research += 1
            return SimpleNamespace(find_elements=lambda *args: [object()])

        def js(self, script, *args):
            if "hubSelect" in script:
                return "2926" if self.research == 1 else "2947"
            if "rDetails table" in script:
                return "0"
            raise AssertionError(script)

        def load_factor(self):
            return 0.8

        def fuel_cost_basis(self):
            return 650

        def co2_cost_basis(self):
            return 125

    assert create_routes(Bot(), 2) == 2
    assert called == [("2926", "645"), ("2947", "645")]
