"""Every dispatch decision must be observable, even when no duplicates exist."""
from __future__ import annotations

import logging

from bot import Bot
from route_registry import RouteRegistry, endpoint
from test_route_readiness_and_departure_policy import FakeDepartBot


def registry_with_pair(tmp_path):
    registry = RouteRegistry(tmp_path / "routes.json")
    registry.record("11", "PP-11", "A320", endpoint(code="DAC"), endpoint(code="OSL"), source="game")
    registry.record("22", "PP-22", "A320", endpoint(code="OSL"), endpoint(code="DAC"), source="game")
    return registry


def test_allowed_duplicate_uses_bulk_but_reports_unconfirmed_dispatch(tmp_path, monkeypatch, caplog):
    import bot as module

    reg = registry_with_pair(tmp_path)
    monkeypatch.setattr(module, "RouteRegistry", lambda: reg)
    fake = FakeDepartBot(allow=True)
    with caplog.at_level(logging.INFO, logger="am4bot.vuelos"):
        Bot._depart_all(fake)
    assert fake.clicked == 1
    status = reg.snapshot()["last_dispatch"]
    assert status["mode"] == "geral"
    assert status["duplicates_known"] == 1
    assert status["status"] == "comando_geral_enviado_sem_confirmacao_individual"
    assert status["departed"] == 0
    assert "permitir duplicidades=SIM" in caplog.text
    assert "comando geral enviado" in caplog.text


def test_disallowed_duplicate_explicitly_disabled_selective_is_reported(tmp_path, monkeypatch):
    import bot as module

    reg = registry_with_pair(tmp_path)
    monkeypatch.setattr(module, "RouteRegistry", lambda: reg)
    fake = FakeDepartBot(allow=False, block_depart=True)
    Bot._depart_all(fake)
    assert fake.clicked == 0
    status = reg.snapshot()["last_dispatch"]
    assert status["mode"] == "bloqueado"
    assert status["status"] == "duplicidades_sem_despacho_seletivo"
    assert status["duplicates_known"] == 1


def test_simulation_without_duplicates_still_records_bulk_plan(tmp_path, monkeypatch, caplog):
    import bot as module

    reg = RouteRegistry(tmp_path / "routes.json")
    reg.record("11", "PP-11", "A320", endpoint(code="DAC"), endpoint(code="OSL"), source="game")
    monkeypatch.setattr(module, "RouteRegistry", lambda: reg)
    fake = FakeDepartBot(allow=False)
    fake.dry_run = True
    with caplog.at_level(logging.INFO, logger="am4bot.vuelos"):
        Bot._depart_all(fake)
    assert fake.clicked == 0
    status = reg.snapshot()["last_dispatch"]
    assert status["mode"] == "geral"
    assert status["simulation"] is True
    assert status["status"] == "simulacao_geral"
    assert "simulação=SIM" in caplog.text


def test_auto_depart_disabled_explains_missing_dispatch_logs(tmp_path, monkeypatch, caplog):
    import bot as module

    reg = RouteRegistry(tmp_path / "routes.json")
    monkeypatch.setattr(module, "RouteRegistry", lambda: reg)

    class Fake:
        dry_run = True
        _language_checked = True

        class Config:
            def get_bool(self, *args):
                return False

            def get(self, *args):
                return ""

        config = Config()

        def _ensure_session(self):
            pass

        def _guard(self, func, what):
            # Execute only the diagnostic write, not any game operations.
            if what == "registrar status de decolagem":
                func()
            if what == "decolar aeronaves":
                raise AssertionError("Disabled departure should never be called")

        def __getattr__(self, _):
            return lambda *args, **kwargs: None

    with caplog.at_level(logging.INFO, logger="am4bot.vuelos"):
        Bot._cycle(Fake())
    status = reg.snapshot()["last_dispatch"]
    assert status["mode"] == "desativado"
    assert status["simulation"] is True
    assert status["status"] == "decolagem_automatica_desativada"
    assert "automático DESATIVADO" in caplog.text
