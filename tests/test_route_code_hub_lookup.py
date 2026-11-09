"""Safe airport-code -> live game hub-ID lookup for duplicate-route proposals."""
from __future__ import annotations

import logging

from fleet import RouteCandidate, resolve_duplicate_routes
from gamemode import EASY
from route_airports import code_from_candidate, match_hub_options
from route_registry import RouteRegistry, eligible_for_reroute, endpoint


def test_unique_hub_matches_either_direction():
    hubs = [
        {"id": "145", "text": "Dhaka — DAC", "code": "", "title": ""},
        {"id": "999", "text": "Guarulhos (GRU)", "code": "", "title": ""},
    ]
    one = match_hub_options("OSL", "DAC", hubs)
    two = match_hub_options("DAC", "OSL", hubs)
    assert one == two
    assert one.airport_id == "145"
    assert one.code == "DAC"
    assert one.opposite_code == "OSL"


def test_hub_match_refuses_ambiguous_or_unlabeled_options():
    assert match_hub_options("OSL", "DAC", [
        {"id": "145", "text": "Dhaka (DAC)"},
        {"id": "146", "text": "Oslo (OSL)"},
    ]) is None
    assert match_hub_options("OSL", "DAC", [
        {"id": "145", "text": "Dhaka"},
    ]) is None
    assert match_hub_options("OSL", "DAC", [
        {"id": "../evil", "text": "DAC"},
    ]) is None


def test_airport_code_requires_explicit_token():
    assert code_from_candidate({"code": "SIN", "name": "Singapore"}) == "SIN"
    assert code_from_candidate({"name": "Singapore (SIN)"}) == "SIN"
    assert code_from_candidate({"name": "SIN - Singapore"}) == "SIN"
    assert code_from_candidate({"name": "Singapore"}) == ""
    assert code_from_candidate({"code": "Some random city", "name": "Oslo (OSL)"}) == "OSL"


def test_code_only_reroute_requires_hub_and_fresh_ground_verification(tmp_path):
    registry = RouteRegistry(tmp_path / "registry.json")
    assert registry.record(
        "a", "PP-1", "A320", endpoint(code="DAC"), endpoint(code="OSL"),
        source="game", at_base=True
    )
    row = registry.snapshot()["relations"][0]
    assert not eligible_for_reroute(row)
    assert eligible_for_reroute(row, verified_hub=True, now=row["game_verified_at"] + 10)
    assert not eligible_for_reroute(row, verified_hub=True, now=row["game_verified_at"] + 185)
    registry.observe("a", at_base=False)
    assert not eligible_for_reroute(registry.snapshot()["relations"][0], verified_hub=True)


def test_duplicate_can_propose_new_destination_from_live_hub_only(tmp_path, monkeypatch, caplog):
    registry = RouteRegistry(tmp_path / "routes.json")
    assert registry.record("101", "PP-0103-2", "A320",
                           endpoint(code="DAC"), endpoint(code="OSL"),
                           source="game", at_base=True)
    assert registry.record("202", "PP-0103-10", "A320",
                           endpoint(code="OSL"), endpoint(code="DAC"),
                           source="game", at_base=True)

    class Config:
        def get_bool(self, section, key):
            return True

        def get_int(self, section, key, default=0):
            return default

    class Bot:
        stopping = False
        dry_run = True
        config = Config()
        mode = EASY

        def open_popup(self, *args):
            pass

        def ajax(self, *args):
            return object()

        def js(self, code, *args):
            if "select.options" in code:
                return [{"id": "145", "text": "DAC — Dhaka", "code": ""}]
            if "document.getElementById('hubSelect')" in code:
                return True
            raise AssertionError("unexpected game query")

        def load_factor(self):
            return 0.8

        def fuel_cost_basis(self):
            return 650

        def co2_cost_basis(self):
            return 125

    monkeypatch.setattr("fleet.load_market", lambda: [{"name": "A320"}])
    monkeypatch.setattr(
        "fleet.find_model",
        lambda market, model: {"speed": 800, "fuel": 7, "capacity": 180, "range": 6000},
    )
    seen = []

    def fake_search(bot, hub_id, max_distance, min_runway):
        seen.append(hub_id)
        return [
            RouteCandidate("201", "Oslo (OSL)", 600, 1800, 100, 0, 9000, "OSL"),
            RouteCandidate("301", "Singapore (SIN)", 1700, 1800, 200, 30, 9000, "SIN"),
        ]

    monkeypatch.setattr("fleet.search_routes", fake_search)
    with caplog.at_level(logging.INFO, logger="am4bot.rutas"):
        assert resolve_duplicate_routes(Bot(), registry, 2) == 0
    assert seen == ["145"]
    affected = next(r for r in registry.snapshot()["relations"] if r["registration"] == "PP-0103-10")
    assert affected["status"] == "prevalidacao_de_rota_pendente"
    assert affected["proposal"]["destination_code"] == "SIN"
    assert affected["proposal"]["origin_code"] == "DAC"
    assert affected["proposal"]["profit_per_day"] > 0
    assert registry.snapshot()["duplicate_routes"] == 1
    assert "aeroporto DAC" in caplog.text
