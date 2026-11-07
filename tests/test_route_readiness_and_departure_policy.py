"""Duplicate route decisions must distinguish ground evidence and block bulk departures."""
from __future__ import annotations

import logging
from types import SimpleNamespace


from bot import Bot
from route_registry import RouteRegistry, eligible_for_reroute, endpoint, reroute_block_reason


def test_reason_explains_dac_ground_block_while_lax_is_ready_for_simulation(tmp_path):
    registry = RouteRegistry(tmp_path / "routes.json")
    dac, osl = endpoint(code="DAC"), endpoint(code="OSL")
    lax, pbm = endpoint(code="LAX"), endpoint(code="PBM")
    registry.record("24133209", "PP-0103-10", "A320", dac, osl,
                    source="game", at_base=False)
    registry.record("24265130", "PP-141-7", "A320", lax, pbm,
                    source="game", at_base=True)
    rows = {r["aircraft_id"]: r for r in registry.snapshot()["relations"]}
    assert reroute_block_reason(rows["24133209"], verified_hub=True) == "aeronave_fora_da_base"
    assert reroute_block_reason(rows["24265130"], verified_hub=True) is None
    assert not eligible_for_reroute(rows["24133209"], verified_hub=True)
    assert eligible_for_reroute(rows["24265130"], verified_hub=True)


def test_unknown_base_manual_route_and_expired_reading_have_distinct_reasons(tmp_path):
    registry = RouteRegistry(tmp_path / "routes.json")
    dac, osl = endpoint(code="DAC"), endpoint(code="OSL")
    registry.record("a", "A", "A320", dac, osl, source="registro_manual")
    record = registry.snapshot()["relations"][0]
    assert reroute_block_reason(record, verified_hub=True) == "rota_nao_confirmada_no_jogo"
    registry.record("a", "A", "A320", dac, osl, source="game")
    record = registry.snapshot()["relations"][0]
    assert reroute_block_reason(record, verified_hub=True) == "localizacao_nao_confirmada"
    registry.record("a", "A", "A320", dac, osl, source="game", at_base=True)
    record = registry.snapshot()["relations"][0]
    assert reroute_block_reason(record, verified_hub=False) == "aeroportos_nao_confirmados"
    assert reroute_block_reason(
        record, verified_hub=True, now=record["game_verified_at"] + 181
    ) == "comprovacao_desatualizada"


class FakeButton:
    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        return ""


class FakeDepartBot:
    dry_run = False

    def __init__(self, allow: bool = False):
        self.allow = allow
        self.clicked = 0
        self.closed = 0
        self._stop = SimpleNamespace(wait=lambda x: None)

        class Config:
            def get_bool(_, section, name, default=False):
                if name == "allow_duplicate_routes":
                    return allow
                if name == "telegram_departures":
                    return False
                return default
        self.config = Config()

    def open_popup(self, *args):
        pass

    def close_popup(self, *args):
        self.closed += 1

    def _sel(self, selector):
        return selector

    def _find(self, *args, **kwargs):
        return FakeButton()

    def pause(self, *args):
        pass

    def click_element(self, *args):
        self.clicked += 1

    def count(self, *args):
        pass


def test_bulk_depart_blocked_by_known_duplicate_routes(tmp_path, monkeypatch, caplog):
    import bot as bot_module

    registry = RouteRegistry(tmp_path / "routes.json")
    dac, osl = endpoint(code="DAC"), endpoint(code="OSL")
    registry.record("1", "PP1", "A320", dac, osl, source="game")
    registry.record("2", "PP2", "A320", osl, dac, source="game")
    monkeypatch.setattr(bot_module, "RouteRegistry", lambda: registry)

    fake = FakeDepartBot(allow=False)
    with caplog.at_level(logging.WARNING, logger="am4bot.vuelos"):
        Bot._depart_all(fake)
    assert fake.clicked == 0
    assert fake.closed == 1
    assert "Decolagem geral bloqueada" in caplog.text
    assert "2 aeronaves" in caplog.text


def test_duplicate_policy_explicitly_allowed_keeps_departure_behavior(tmp_path, monkeypatch):
    import bot as bot_module

    registry = RouteRegistry(tmp_path / "routes.json")
    dac, osl = endpoint(code="DAC"), endpoint(code="OSL")
    registry.record("1", "PP1", "A320", dac, osl, source="game")
    registry.record("2", "PP2", "A320", osl, dac, source="game")
    monkeypatch.setattr(bot_module, "RouteRegistry", lambda: registry)

    fake = FakeDepartBot(allow=True)
    Bot._depart_all(fake)
    assert fake.clicked == 1
    assert fake.closed == 1
