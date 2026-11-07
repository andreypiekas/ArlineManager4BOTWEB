"""A live reroute must identify the old route from aircraft details first."""
from __future__ import annotations

from reroute_preflight import check_existing_route
from route_registry import endpoint


def record():
    return {
        "origin": endpoint(code="DAC"),
        "destination": endpoint(code="OSL"),
        "source": "game",
    }


class Bot:
    def __init__(self, result):
        self.result = result
        self.reads = []

    def ajax(self, uri, target):
        self.reads.append((uri, target))
        assert "mode=do" not in uri
        assert "fleet_ground.php" not in uri

    def js(self, script):
        assert "detailsAction" in script
        return self.result


def test_reroute_preflight_reads_real_route_id_with_bidirectional_airport_codes():
    b = Bot({"ground_route_ids": ["99123"], "endpoints": ["OSL", "DAC"],
             "in_flight": False, "has_details": True})
    result = check_existing_route(b, "24133209", record())
    assert result.route_confirmed
    assert result.route_id == "99123"
    assert result.reason == "rota_confirmada"
    assert b.reads == [("fleet_details.php?id=24133209", "detailsAction")]


def test_reroute_preflight_never_confuses_aircraft_id_with_route_id():
    b = Bot({"ground_route_ids": [], "endpoints": ["DAC", "OSL"],
             "in_flight": False, "has_details": True})
    result = check_existing_route(b, "24133209", record())
    assert not result.route_confirmed
    assert result.route_id == ""
    assert result.reason == "id_da_rota_ambigua_ou_ausente"


def test_reroute_preflight_refuses_ambiguous_or_changed_route():
    b = Bot({"ground_route_ids": ["99", "100"], "endpoints": ["DAC", "OSL"],
             "in_flight": False, "has_details": True})
    assert check_existing_route(b, "24133209", record()).reason == "id_da_rota_ambigua_ou_ausente"
    b.result = {"ground_route_ids": ["99"], "endpoints": ["DAC", "GRU"],
                "in_flight": False, "has_details": True}
    assert check_existing_route(b, "24133209", record()).reason == "rota_divergente_dos_detalhes"


def test_reroute_preflight_refuses_aircraft_in_flight():
    b = Bot({"ground_route_ids": ["99"], "endpoints": ["DAC", "OSL"],
             "in_flight": True, "has_details": True})
    assert check_existing_route(b, "24133209", record()).reason == "aeronave_ainda_em_voo"


def test_preflight_missing_panel_does_not_write_or_crash():
    b = Bot(None)
    assert check_existing_route(b, "24133209", record()).reason == "painel_da_aeronave_vazio"
    assert check_existing_route(b, "../oops", record()).reason == "id_aeronave_invalido"
    assert b.reads == [("fleet_details.php?id=24133209", "detailsAction")]
