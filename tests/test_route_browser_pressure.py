"""Route planner must not make heavy Selenium calls for planes still in flight."""
from __future__ import annotations

import logging

import fleet
from route_registry import RouteRegistry, endpoint
from route_strategy import route_research_blocker


def _row(base, *, now=1000, seen=1000, ground=1000):
    return {
        "source": "game", "at_base": base,
        "game_verified_at": seen,
        "grounded_confirmed_at": ground,
    }


def test_route_research_requires_current_game_route_and_actual_ground_evidence():
    assert route_research_blocker(_row(False)) == "aguardando_pouso_para_analise"
    assert route_research_blocker(_row(None)) == "localizacao_nao_confirmada"
    assert route_research_blocker(_row(True, seen=500), now=1000) == "comprovacao_desatualizada"
    assert route_research_blocker(_row(True, ground=500), now=1000) == "comprovacao_desatualizada"
    assert route_research_blocker(_row(True, seen=1000, ground=1000), now=1000) is None
    assert route_research_blocker({**_row(True), "source": "manual"}, now=1000) == "rota_nao_confirmada_no_jogo"


def test_live_research_skipped_for_flying_duplicate_while_proposal_is_preserved(
    tmp_path, monkeypatch, caplog
):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    origin, destination = endpoint(code="DAC"), endpoint(code="OSL")
    registry.record("101", "PP-101", "A320", origin, destination, source="game", at_base=False)
    registry.record("102", "PP-102", "A320", destination, origin, source="game", at_base=False)
    # The second aircraft is the duplicate candidate for a plan.
    prior = {"destination": "SIN", "profit_per_day": 100000, "calculated_at": 100}
    registry.note("102", "simulacao_redirecionamento", proposal=prior)
    monkeypatch.setattr(fleet, "load_market", lambda: [])

    class Config:
        def get_bool(self, section, key):
            return key == "analyze_duplicate_routes"

    class ReadOnlyBot:
        config = Config()
        dry_run = True
        stopping = False

        def open_popup(self, *args):
            raise AssertionError("No route popup when both aircraft are in flight")

        def ajax(self, *args):
            raise AssertionError("No Ajax requests when both aircraft are in flight")

        def js(self, *args):
            raise AssertionError("No Selenium calls when both aircraft are in flight")

    with caplog.at_level(logging.INFO, logger="am4bot.rutas"):
        assert fleet.resolve_duplicate_routes(ReadOnlyBot(), registry, 5) == 0
    rows = {r["aircraft_id"]: r for r in registry.snapshot()["relations"]}
    assert rows["102"]["status"] == "aguardando_pouso_para_analise"
    assert rows["102"]["proposal"] == prior
    assert "0 pesquisas no navegador" in caplog.text
    assert "pesquisa pesada adiada" in caplog.text
