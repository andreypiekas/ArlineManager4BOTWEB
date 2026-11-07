"""Experimental numeric-ID departure is explicit opt-in and one-shot per profile."""
from __future__ import annotations

from selective_batch_depart import targeted_depart
from selective_depart import plan_dispatch
from route_registry import RouteRegistry, endpoint


def make_registry(tmp_path):
    r = RouteRegistry(tmp_path / "route_registry.json")
    a, b, c = [endpoint(code=x) for x in ("DAC", "OSL", "LAX")]
    r.record("101", "PP-101", "A380", a, b, source="game")
    r.record("102", "PP-102", "A380", b, a, source="game")
    r.record("103", "PP-103", "A320", b, c, source="game")
    return r


class FakeGame:
    stopping = False

    def __init__(self, *, enabled=True, dry_run=False, native=True, extra=False):
        self.enabled = enabled
        self.dry_run = dry_run
        self.native = native
        self.extra = extra
        self.requests = []
        self.departed = False
        self.counted = 0

        class Config:
            def get_bool(self, *args):
                return enabled

        self.config = Config()

    def js(self, code, *args):
        if "document.getElementById(\"runme\")" in code:
            return self.native
        if "const read = id" in code:
            inflight = ["101"] if self.departed else []
            if self.extra and self.departed:
                inflight.append("102")
            return {
                "landed": ["102", "103"] if self.departed else ["101", "102", "103"],
                "inflight": inflight,
            }
        raise AssertionError("Unexpected JavaScript query")

    def ajax(self, uri, target):
        assert target == "runme"
        self.requests.append(uri)
        self.departed = True

    def count(self, key):
        assert key == "departures"
        self.counted += 1


def decisions(registry):
    return plan_dispatch(["101", "102", "103"], registry.snapshot(allow_duplicates=False))


def test_disabled_pilot_has_no_network_actions(tmp_path):
    r = make_registry(tmp_path)
    b = FakeGame(enabled=False)
    result = targeted_depart(b, r, decisions(r))
    assert result["status"] == "experimental_desativado"
    assert b.requests == []
    assert r.snapshot()["experimental_departure_pilot"] is None


def test_simulation_is_read_only_and_does_not_claim_the_pilot(tmp_path):
    r = make_registry(tmp_path)
    b = FakeGame(dry_run=True)
    result = targeted_depart(b, r, decisions(r))
    assert result["status"] == "simulacao_lote_experimental"
    assert result["target_id"] == "101"
    assert b.requests == []
    assert r.snapshot()["experimental_departure_pilot"] is None


def test_missing_native_control_blocks_all_requests(tmp_path):
    r = make_registry(tmp_path)
    b = FakeGame(native=False)
    result = targeted_depart(b, r, decisions(r))
    assert result["status"] == "contrato_do_jogo_nao_confirmado"
    assert b.requests == []


def test_one_target_only_then_persistent_lockout(tmp_path):
    r = make_registry(tmp_path)
    b = FakeGame()
    result = targeted_depart(b, r, decisions(r))
    assert b.requests == ["route_depart.php?mode=all&ids=101"]
    assert result["status"] == "decolagem_experimental_confirmada"
    assert result["departed"] == 1
    assert b.counted == 1
    pilot = r.snapshot()["experimental_departure_pilot"]
    assert pilot["aircraft_id"] == "101"
    assert pilot["status"] == "decolagem_experimental_confirmada"

    another = FakeGame()
    result_2 = targeted_depart(another, r, decisions(r))
    assert result_2["status"] == "piloto_experimental_ja_utilizado"
    assert another.requests == []
    assert another.counted == 0


def test_unexpected_extra_departure_fails_closed_and_stays_locked(tmp_path):
    r = make_registry(tmp_path)
    b = FakeGame(extra=True)
    result = targeted_depart(b, r, decisions(r))
    assert result["status"] == "alteracao_inesperada_no_jogo"
    assert result["departed"] == 0
    assert b.requests == ["route_depart.php?mode=all&ids=101"]
    assert r.snapshot()["experimental_departure_pilot"]["status"] == result["status"]


def test_only_duplicate_reserved_or_stale_aircraft_cannot_be_targeted(tmp_path):
    r = make_registry(tmp_path)
    b = FakeGame()
    candidate = [d for d in decisions(r) if d.aircraft_id == "102"]
    assert not candidate[0].approved
    result = targeted_depart(b, r, candidate)
    assert result["status"] == "nenhuma_aeronave_aprovada_agora"
    assert b.requests == []


def test_timeout_after_request_never_retries(tmp_path):
    r = make_registry(tmp_path)

    class TimedOut(FakeGame):
        def ajax(self, uri, target):
            super().ajax(uri, target)
            raise TimeoutError("response lost after sending")

    b = TimedOut()
    result = targeted_depart(b, r, decisions(r))
    assert result["status"] == "pedido_experimental_resultado_desconhecido"
    assert len(b.requests) == 1
    assert r.snapshot()["experimental_departure_pilot"]["status"] == result["status"]
    another = FakeGame()
    assert targeted_depart(another, r, decisions(r))["status"] == "piloto_experimental_ja_utilizado"
    assert another.requests == []
