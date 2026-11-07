"""Selective dispatch: no bulk fallback, only native per-aircraft controls."""
from __future__ import annotations

import logging

from selective_depart import plan_dispatch, selective_dispatch, verified_native_action
from route_registry import RouteRegistry, endpoint


def registry_with_duplicate(tmp_path):
    registry = RouteRegistry(tmp_path / "registry.json")
    dac, osl, lax, pbm = [
        endpoint(code=code) for code in ("DAC", "OSL", "LAX", "PBM")
    ]
    registry.record("101", "PP-A", "A320", dac, osl, source="game")
    registry.record("102", "PP-B", "A320", osl, dac, source="game")
    registry.record("103", "PP-C", "A320", lax, pbm, source="game")
    return registry


def test_plan_keeps_one_per_duplicate_and_approves_unrelated_routes(tmp_path):
    registry = registry_with_duplicate(tmp_path)
    snapshot = registry.snapshot()
    decisions = plan_dispatch(["101", "102", "103", "999"], snapshot)
    by_id = {d.aircraft_id: d for d in decisions}
    assert by_id["101"].approved
    assert by_id["102"].reason == "rota_duplicada_reservada"
    assert by_id["103"].approved
    assert by_id["999"].reason == "rota_nao_identificada"


def test_untrusted_or_global_depart_actions_are_rejected():
    id_ = "24133209"
    accepted = "Ajax('route_depart.php?mode=single&ids=24133209','runme',this)"
    assert verified_native_action(id_, [{"value": accepted}]) == accepted
    assert verified_native_action(id_, [{"value": "route_depart.php?mode=all&ids=x"}]) == ""
    assert verified_native_action(id_, [{"value": "route_depart.php?mode=all&ids=24133209,24133201"}]) == ""
    assert verified_native_action(id_, [{"value": "route_depart.php?mode=do&id=24133201"}]) == ""
    assert verified_native_action(id_, [{"value": accepted}, {"value": accepted}]) == ""
    assert verified_native_action(id_, [{"value": "route_depart.php?mode=all&ids=24133209"}]) != ""


def test_report_is_read_only_when_game_has_only_bulk_depart_all(tmp_path, caplog):
    registry = registry_with_duplicate(tmp_path)

    class Bot:
        dry_run = False
        stopping = False

        def js(self, code, *args):
            return [
                {"id": "101", "native_actions": []},
                {"id": "102", "native_actions": []},
                {"id": "103", "native_actions": []},
            ]

    with caplog.at_level(logging.INFO, logger="am4bot.vuelos"):
        summary = selective_dispatch(Bot(), registry)
    assert summary["approved"] == 2
    assert summary["blocked"] == 1
    assert summary["native_individual"] == 0
    assert summary["departed"] == 0
    assert summary["status"] == "controle_individual_nao_disponivel"
    assert registry.snapshot()["last_dispatch"]["blocked_aircraft"][0]["reason"] == "rota_duplicada_reservada"
    assert "Nunca usa Decolar todas" in caplog.text


def test_simulation_exposes_native_selective_plan_without_click(tmp_path):
    registry = registry_with_duplicate(tmp_path)

    class Bot:
        dry_run = True
        stopping = False

        def js(self, code, *args):
            return [
                {"id": "101", "native_actions": [
                    {"value": "Ajax('route_depart.php?mode=single&ids=101','runme',this)"}
                ]},
                {"id": "102", "native_actions": []},
            ]

    summary = selective_dispatch(Bot(), registry)
    assert summary["approved"] == 1
    assert summary["native_individual"] == 1
    assert summary["blocked"] == 1
    assert summary["departed"] == 0
    assert registry.snapshot()["last_dispatch"]["status"] == "simulacao"


def test_stale_game_route_is_not_authorized(tmp_path):
    registry = registry_with_duplicate(tmp_path)
    snap = registry.snapshot()
    row = next(r for r in snap["relations"] if r["aircraft_id"] == "101")
    decisions = plan_dispatch(["101"], snap, now=row["game_verified_at"] + 181)
    assert decisions[0].reason == "leitura_de_rota_expirada"
