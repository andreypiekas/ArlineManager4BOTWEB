"""Duplicate-route diagnostic must show both aircraft and the precise blocker."""
from __future__ import annotations

import logging

from fleet import resolve_duplicate_routes
from route_registry import RouteRegistry, endpoint


class NoWriteBot:
    stopping = False
    dry_run = True
    config = object()  # Config is read but never used while numeric airport IDs are missing.

    def __getattr__(self, name):
        raise AssertionError(f"Unexpected game action: {name}")


def test_duplicate_logged_with_aircraft_and_missing_numeric_airport_ids(tmp_path, caplog, monkeypatch):
    monkeypatch.setattr("fleet.load_market", lambda: [])
    registry = RouteRegistry(tmp_path / "routes_registry.json")
    one, two = endpoint(code="DUB"), endpoint(code="GRU")
    assert registry.record("101", "XP-101", "A320", one, two, source="game")
    assert registry.record("202", "XP-202", "A320", two, one, source="game")
    with caplog.at_level(logging.INFO, logger="am4bot.rutas"):
        result = resolve_duplicate_routes(NoWriteBot(), registry, 2)
    assert result == 0
    log = caplog.text
    assert "duplicidade na rota" in log
    assert "XP-101" in log and "XP-202" in log
    assert "IDs dos aeroportos ausentes" in log
    assert "DUB ↔ GRU" in log
    snapshot = registry.snapshot()
    assert snapshot["duplicate_routes"] == 1
    assert any(r["status"] == "aguardando_identificacao_da_rota" for r in snapshot["relations"])
