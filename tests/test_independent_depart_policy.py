"""Deixar de criar rotas não pode impedir que aviões com rotas existentes decolem."""
from __future__ import annotations

import logging

import pytest

from bot import Bot
from route_registry import RouteRegistry, endpoint
from test_route_readiness_and_departure_policy import FakeDepartBot


def _registry(tmp_path):
    registry = RouteRegistry(tmp_path / "routes.json")
    for idx in range(11):
        # The reported account has 11 duplicated route pairs.
        origin = endpoint(code="DAC" if idx % 2 == 0 else "LAX")
        destination = endpoint(code="OSL" if idx % 2 == 0 else "PBM")
        registry.record(str(100 + idx * 2), f"PP-{idx}-A", "A380", origin, destination, source="game")
        registry.record(str(101 + idx * 2), f"PP-{idx}-B", "A380", destination, origin, source="game")
    return registry


@pytest.mark.parametrize("auto_route", [False, True])
def test_existing_duplicate_flights_depart_independently_of_route_creation(
    tmp_path, monkeypatch, caplog, auto_route
):
    import bot as module

    registry = _registry(tmp_path)
    assert registry.snapshot()["duplicate_routes"] == 2  # two unique airport pairs
    monkeypatch.setattr(module, "RouteRegistry", lambda: registry)
    fake = FakeDepartBot(
        allow=False, block_depart=False, auto_route=auto_route
    )
    with caplog.at_level(logging.INFO, logger="am4bot.vuelos"):
        Bot._depart_all(fake)
    assert fake.clicked == 1
    assert fake.closed == 1
    report = registry.snapshot()["last_dispatch"]
    assert report["mode"] == "geral"
    assert report["status"] == "comando_geral_enviado_sem_confirmacao_individual"
    assert "permitir novas duplicidades=NÃO" in caplog.text
    assert "bloquear decolagens duplicadas=NÃO" in caplog.text
    assert f"rotas automáticas={'SIM' if auto_route else 'NÃO'}" in caplog.text


def test_explicit_departure_block_keeps_fleet_stopped_when_selective_off(tmp_path, monkeypatch):
    import bot as module

    registry = _registry(tmp_path)
    monkeypatch.setattr(module, "RouteRegistry", lambda: registry)
    fake = FakeDepartBot(allow=False, block_depart=True, auto_route=False)
    Bot._depart_all(fake)
    assert fake.clicked == 0
    assert registry.snapshot()["last_dispatch"]["mode"] == "bloqueado"


def test_manual_interlock_with_selective_option_never_uses_bulk_button(tmp_path, monkeypatch):
    import bot as module

    registry = _registry(tmp_path)
    monkeypatch.setattr(module, "RouteRegistry", lambda: registry)
    seen = []

    def fake_selective(bot, registry_arg):
        assert registry_arg is registry
        seen.append(bot)

    monkeypatch.setattr(module, "selective_dispatch", fake_selective)
    fake = FakeDepartBot(allow=False, block_depart=True, auto_route=False)
    base_config = fake.config

    class WithSelective:
        def get_bool(self, section, name, default=False):
            return True if name == "selective_depart" else base_config.get_bool(section, name, default)

    fake.config = WithSelective()
    Bot._depart_all(fake)
    assert seen == [fake]
    assert fake.clicked == 0


def test_dry_run_still_prevents_depart_even_when_interlock_off(tmp_path, monkeypatch):
    import bot as module

    registry = _registry(tmp_path)
    monkeypatch.setattr(module, "RouteRegistry", lambda: registry)
    fake = FakeDepartBot(allow=False, block_depart=False, auto_route=False)
    fake.dry_run = True
    Bot._depart_all(fake)
    assert fake.clicked == 0
    assert registry.snapshot()["last_dispatch"]["status"] == "simulacao_geral"
