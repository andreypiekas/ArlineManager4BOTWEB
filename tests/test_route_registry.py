"""Persistent route registry: canonical direction, history and conservative identities."""
import json

from route_registry import RouteRegistry, endpoint, route_key, same_route


def test_direction_does_not_change_route_identity():
    dub = endpoint("101", "DUB", "Dublin")
    gru = endpoint("202", "GRU", "São Paulo")
    a = {"origin": dub, "destination": gru}
    b = {"origin": gru, "destination": dub}
    assert route_key(dub, gru) == route_key(gru, dub)
    assert same_route(a, b)
    assert not same_route(a, {"origin": dub, "destination": endpoint("999", "LHR")})


def test_duplicate_detection_persists_and_preserves_history(tmp_path):
    path = tmp_path / "routes_registry.json"
    registry = RouteRegistry(path)
    dub = endpoint("101", "DUB")
    gru = endpoint("202", "GRU")
    assert registry.record("ac1", "XP-001", "A380", dub, gru, source="criacao_confirmada")
    assert registry.record("ac2", "XP-002", "B777", gru, dub, source="jogo")
    assert not registry.record("ac3", "XP-003", "A320", dub, dub)
    report = RouteRegistry(path).snapshot(allow_duplicates=False)
    assert report["total"] == 2
    assert report["duplicate_routes"] == 1
    assert report["affected_aircraft"] == 2
    assert {item["registration"] for item in report["relations"]} == {"XP-001", "XP-002"}
    assert report["history"][0]["action"] == "rota_registrada"
    assert registry.is_occupied(dub, gru, except_aircraft="ac1")
    assert registry.is_occupied(gru, dub, except_aircraft="ac2")


def test_unrecognized_airport_identity_cannot_create_a_fake_route(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    assert not registry.record("a", "XP", "A320", endpoint(), endpoint("55"))
    assert registry.observe("a", "XP", "A320", at_base=False)
    snap = registry.snapshot()
    assert snap["total"] == 1
    assert snap["relations"][0]["status"] == "rota_nao_identificada"
    assert not registry.is_occupied(endpoint("12"), endpoint("55"))


def test_manual_names_normalize_accents_and_detect_reverse(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    assert registry.record("a", "A", "777", endpoint(name="São Paulo"), endpoint(name="Dublin"))
    assert registry.record("b", "B", "777", endpoint(name="DUBLIN"), endpoint(name="SAO PAULO"))
    assert registry.snapshot()["duplicate_routes"] == 1


def test_id_mismatch_with_same_airport_code_must_not_be_assumed_equal():
    dub = endpoint("123", "DUB")
    invalid = endpoint("998", "DUB")
    gru = endpoint("201", "GRU")
    assert not same_route({"origin": dub, "destination": gru},
                          {"origin": invalid, "destination": gru})


def test_partial_scan_does_not_erase_prior_confirmed_route(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    a, b = endpoint("101"), endpoint("202")
    registry.record("a", "XP-1", "A320", a, b, at_base=True)
    registry.observe("a", "XP-1", "A320", at_base=False)
    row = registry.snapshot()["relations"][0]
    assert row["origin"]["id"] == "101"
    assert row["destination"]["id"] == "202"
    assert row["at_base"] is False
    assert row["status"] == "ativa"


def test_proposal_does_not_overwrite_current_route(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    a, b = endpoint("101"), endpoint("202")
    registry.record("a", "XP", "A320", a, b)
    proposal = {"destination_id": "303", "profit_per_day": 13500}
    assert registry.note("a", "aguardando_aeronave_na_base", proposal=proposal)
    assert registry.snapshot()["relations"][0]["destination"]["id"] == "202"
    assert json.loads(registry.path.read_text(encoding="utf-8"))["aircraft"]["a"]["proposal"] == proposal
    # Reading the same route from the game must not erase a pending proposal.
    registry.record("a", "XP", "A320", a, b, source="jogo")
    assert registry.snapshot()["relations"][0]["proposal"] == proposal
    # A confirmed reroute replaces it and clears the old proposal.
    registry.record("a", "XP", "A320", a, endpoint("303"), source="redirecionamento")
    assert "proposal" not in registry.snapshot()["relations"][0]


def test_web_route_workplace_has_dedicated_navigation():
    from conftest import ROOT
    page = (ROOT / "assets/web/index.html").read_text(encoding="utf-8")
    assert 'id="routesView" hidden' in page
    assert 'href="#routes"' in page
    assert 'id="routesTable"' in page
    assert 'api("/api/routes")' in page
    assert 'api("/api/routes", {action: "register", ...data})' in page


def test_game_observation_required_before_reroute(tmp_path):
    from route_registry import eligible_for_reroute
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    first, last = endpoint("101"), endpoint("202")
    registry.record("a", "XP", "A320", first, last, source="registro_manual", at_base=True)
    assert not eligible_for_reroute(registry.snapshot()["relations"][0])
    registry.record("a", "XP", "A320", first, last, source="game", at_base=True)
    verified = registry.snapshot()["relations"][0]
    assert eligible_for_reroute(verified, now=verified["game_verified_at"] + 30)
    assert not eligible_for_reroute(verified, now=verified["game_verified_at"] + 181)
    registry.observe("a", "XP", "A320", at_base=False)
    assert not eligible_for_reroute(registry.snapshot()["relations"][0])


def test_parked_without_route_invalidates_old_assignment(tmp_path):
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    first, last = endpoint("101"), endpoint("202")
    registry.record("a", "XP", "A320", first, last)
    registry.unassign("a", "XP", "A320")
    snapshot = registry.snapshot()
    assert snapshot["relations"][0]["status"] == "sem_rota"
    assert snapshot["duplicate_routes"] == 0
    assert not registry.is_occupied(first, last)
    assert snapshot["history"][0]["action"] == "rota_removida_no_jogo"
