"""Read-only diagnosis for route pairs whose endpoints cannot be matched to company hubs."""
import logging
from types import SimpleNamespace

from fleet import audit_routes
from route_airports import explain_hub_options
from route_registry import RouteRegistry


def test_hub_selector_can_omit_both_route_endpoints():
    result = explain_hub_options("DAC", "OSL", [
        {"id": "11", "text": "São Paulo (GRU)", "code": "GRU"},
        {"id": "12", "text": "Chapecó (XAP)", "code": "XAP"},
    ])
    assert result["reason"] == "nenhuma_ponta_da_rota_nas_bases"
    assert result["total_options"] == 2
    assert result["valid_ids"] == 2
    assert result["matched"] == {"DAC": [], "OSL": []}
    assert len(result["samples"]) == 2


def test_hub_options_without_codes_do_not_guess_city():
    result = explain_hub_options("DAC", "OSL", [
        {"id": "90001", "text": "São Paulo", "code": ""},
        {"id": "90002", "text": "Chapecó", "code": ""},
    ])
    assert result["reason"] == "etiquetas_sem_codigos_aeroportos"


def test_ambiguous_hubs_are_not_selected():
    result = explain_hub_options("DAC", "OSL", [
        {"id": "11", "text": "Dhaka (DAC)", "code": "DAC"},
        {"id": "12", "text": "Oslo (OSL)", "code": "OSL"},
    ])
    assert result["reason"] == "bases_ambiguas"


def test_cached_maintenance_grounded_status_is_reused_for_route_audit(tmp_path, caplog):
    registry = RouteRegistry(tmp_path / "routes.json")
    rows = [
        {"aircraft_id": "101", "registration": "PP-101", "model": "A320",
         "origin_code": "DAC", "destination_code": "OSL", "in_flight": False,
         "at_base": None},
        {"aircraft_id": "102", "registration": "PP-102", "model": "A320",
         "origin_code": "OSL", "destination_code": "DAC", "in_flight": True,
         "at_base": None},
        {"aircraft_id": "103", "registration": "PP-103", "model": "A320",
         "origin_code": "DAC", "destination_code": "SIN", "in_flight": False,
         "at_base": None},
    ]

    class FakeBot:
        def js(self, _):
            return rows

        def recent_fleet(self, age):
            assert age == 180
            return [
                SimpleNamespace(id="101", at_base=True),
                SimpleNamespace(id="102", at_base=True),
            ]

    with caplog.at_level(logging.INFO, logger="am4bot.rutas"):
        audit_routes(FakeBot(), registry)
    snapshot = registry.snapshot()
    records = {r["aircraft_id"]: r for r in snapshot["relations"]}
    assert records["101"]["at_base"] is True
    assert records["101"]["grounded_confirmed_at"] > 0
    assert records["102"]["at_base"] is False
    assert "grounded_confirmed_at" not in records["102"]
    assert "at_base" not in records["103"]
    assert "manutenção confirmou localização de 1 aeronaves" in caplog.text
    assert snapshot["last_scan"]["identified"] == 3
