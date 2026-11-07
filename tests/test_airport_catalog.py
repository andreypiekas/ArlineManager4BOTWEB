"""Airport crosswalk: game IDs are consistent with the latest observed hub selector."""
from __future__ import annotations

from airport_catalog import by_code, by_id, game_code, same_airport_identity
from route_airports import code_from_candidate, explain_hub_options, match_hub_options
from route_registry import endpoint, same_route


def test_known_game_airport_ids_from_live_2026_11_07_log():
    assert by_id("2926").iata == "XAP"
    assert by_id("2947").icao == "SBGR"
    assert by_id("1275").iata == "DTW"
    assert by_id("465").iata == "TXL"
    assert by_id("2499") is not None
    assert by_code("DAC").game_id == "3499"
    assert by_code("OSL").game_id == "645"
    assert by_code("LAX").game_id == "1440"
    assert by_code("PBM").game_id == "3146"


def test_hub_options_without_iata_labels_get_game_codes_without_guessing():
    report = explain_hub_options("DAC", "OSL", [
        {"id": "2926", "text": "Chapecó, Brazil", "code": ""},
        {"id": "2947", "text": "São Paulo Guarulhos, Brazil", "code": ""},
        {"id": "1275", "text": "Detroit Metrop., United States", "code": ""},
        {"id": "465", "text": "Berlin Tegel, Germany", "code": ""},
        {"id": "2499", "text": "Dubai, United Arab Emirates", "code": ""},
    ])
    assert report["reason"] == "nenhuma_ponta_da_rota_nas_bases"
    assert report["labels_with_possible_codes"] == 5
    assert report["valid_ids"] == 5
    assert "2926: Chapecó, Brazil [XAP/SBCH]" in report["samples"]


def test_hub_matching_is_bidirectional_and_resolves_icao_from_id():
    options = [{"id": "3499", "text": "Dhaka, Bangladesh"},
               {"id": "2926", "text": "Chapecó, Brazil"}]
    found = match_hub_options("OSL", "DAC", options)
    assert found is not None
    assert found.airport_id == "3499"
    assert found.code == "DAC"
    assert match_hub_options("DAC", "OSL", options) == found
    assert match_hub_options("VGZR", "ENGM", options).airport_id == "3499"


def test_neither_route_endpoint_is_owned_hub_means_no_reroute_assumption():
    options = [{"id": "2926", "text": "Chapecó"},
               {"id": "2947", "text": "São Paulo"}]
    assert match_hub_options("DAC", "OSL", options) is None
    assert match_hub_options("LAX", "PBM", options) is None


def test_candidate_airport_code_can_be_derived_from_live_game_id():
    assert code_from_candidate({"arr": "645", "name": "Oslo"}) == "OSL"
    assert code_from_candidate({"arr": "3146", "name": "Zandery"}) == "PBM"
    assert game_code("2926") == "XAP"
    assert game_code("2926", "SBCH") == "SBCH"
    assert game_code("invalid") == ""


def test_undirected_identity_matches_catalog_id_iata_and_icao():
    first = {"origin": endpoint("3499"), "destination": endpoint("645")}
    opposite = {"origin": endpoint(code="ENGM"), "destination": endpoint(code="DAC")}
    assert same_route(first, opposite)
    assert same_airport_identity(endpoint("645"), endpoint(code="OSL"))
    assert same_airport_identity(endpoint("645"), endpoint(code="ENGM"))
    assert not same_airport_identity(endpoint("645"), endpoint(code="PBM"))


def test_conflicting_game_ids_never_match_even_if_codes_repeat():
    a = endpoint("645", "OSL")
    b = endpoint("3499", "OSL")
    assert not same_airport_identity(a, b)
    assert not same_airport_identity(endpoint("645", "DAC"), endpoint(code="DAC"))
