"""Sincronização periódica do caixa com o jogo sem concorrer com Selenium."""
from __future__ import annotations

import logging
import threading
import time
from configparser import ConfigParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from selenium.common.exceptions import WebDriverException

from bot import Bot, Stats
from dashboard import snapshot
from settings_schema import ALL_FIELDS, clamp_settings


ROOT = Path(__file__).resolve().parents[1]


class FakeConfig:
    def __init__(self, interval=60):
        self.interval = interval

    def get_int(self, section, key, fallback=0):
        return {
            "cash_sync_seconds": self.interval,
            "cycle_min_minutes": 5,
            "cycle_max_minutes": 5,
        }.get(key, fallback)


class Driver:
    def __init__(self, exception=None):
        self.calls = 0
        self.exception = exception

    def refresh(self):
        self.calls += 1
        if self.exception:
            raise self.exception


def bot_for_cash(*, money=1000, driver=None, interval=60):
    bot = Bot.__new__(Bot)
    bot.config = FakeConfig(interval)
    bot.driver = driver or Driver()
    bot._stop = threading.Event()
    bot._wake = threading.Event()
    bot._stats_lock = threading.Lock()
    bot._stats = Stats(money=money)
    bot._next_event = None
    bot.next_cycle_at = None
    bot._is_logged_in = lambda timeout: True
    bot.read_money = lambda: 1250
    return bot


def test_poll_le_paginas_do_jogo_e_atualiza_valor_externo(caplog):
    bot = bot_for_cash()
    before = time.time()
    with caplog.at_level(logging.INFO):
        assert bot._sync_cash_from_game() is True
    result = bot.stats()
    assert result.money == 1250
    assert result.money_read_at is not None and result.money_read_at >= before
    assert bot.driver.calls == 1
    assert "Saldo sincronizado com o jogo" in caplog.text


def test_mantem_ultimo_saldo_se_leitura_nao_concluir():
    bot = bot_for_cash(money=1990)
    bot.read_money = lambda: None
    assert bot._sync_cash_from_game() is False
    assert bot.stats().money == 1990
    assert bot.stats().money_read_at is None
    assert bot.driver.calls == 1


def test_sessao_perdida_solicita_novo_ciclo_sem_exibir_saldo_falso():
    bot = bot_for_cash()
    bot._is_logged_in = lambda timeout: False
    assert bot._sync_cash_from_game() is False
    assert bot._wake.is_set()
    assert bot.stats().money == 1000


def test_sincronizacao_nao_atua_com_bot_parado():
    bot = bot_for_cash()
    bot._stop.set()
    assert bot._sync_cash_from_game() is False
    assert bot.driver.calls == 0


def test_desconexao_do_webdriver_eh_propagada_ao_supervisor():
    bot = bot_for_cash(driver=Driver(WebDriverException("Connection refused")))
    with pytest.raises(WebDriverException):
        bot._sync_cash_from_game()


def test_valor_estimado_apos_compra_nao_finge_ser_leitura_do_jogo():
    bot = bot_for_cash()
    bot.update_stats(money=800)
    assert bot.stats().money == 800
    assert bot.stats().money_read_at is None


def test_durante_espera_sincroniza_sem_disparar_ciclo():
    bot = bot_for_cash()
    calls = []

    class Wake:
        def __init__(self):
            self.ticks = 0
            self.cleared = False

        def wait(self, timeout):
            assert 0 < timeout <= 60
            self.ticks += 1
            return self.ticks == 2

        def is_set(self):
            return False

        def clear(self):
            self.cleared = True

    bot._wake = Wake()
    bot._sync_cash_from_game = lambda: calls.append("refresh")
    bot._sleep_until_next_cycle()
    assert calls == ["refresh"]
    assert bot._wake.cleared
    assert bot.next_cycle_at is None
    assert bot.driver.calls == 0


def test_campo_ajustavel_de_30_a_600_segundos():
    ini = ConfigParser()
    ini.read(ROOT / "config/defaults.ini", encoding="utf-8")
    assert ini.getint("settings", "cash_sync_seconds") == 60
    assert "cash_sync_seconds" in dict(ALL_FIELDS)
    assert clamp_settings({"cash_sync_seconds": 5})["cash_sync_seconds"] == 30
    assert clamp_settings({"cash_sync_seconds": 900})["cash_sync_seconds"] == 600


def test_web_apresenta_horario_da_ultima_leitura_e_avisa_quando_desatualizado():
    html = (ROOT / "assets/web/index.html").read_text(encoding="utf-8")
    assert "s.money_read_at" in html
    assert "Saldo conferido às {x}" in html
    assert "Leitura do saldo desatualizada: {x}" in html
    assert "s.money_sync_seconds" in html
    assert "setInterval(tick, 2000)" in html


def test_snapshot_expoe_fonte_e_frequencia_da_leitura():
    class Config:
        def get_int(self, section, key, fallback=0):
            return 60 if key == "cash_sync_seconds" else fallback

        def get(self, section, key, fallback=""):
            return "auto" if key == "goal_model" else fallback

        def get_bool(self, section, key, fallback=False):
            return False

    # Este teste usa a projeção dos campos novos, evitando dependências de dados reais.
    class BotView:
        def stats(self):
            return Stats(money=20000, money_read_at=123456.0)

        state = SimpleNamespace(value="Em execução", name="RUNNING")
        next_cycle_at = None
        dry_run = False
        last_error = None

        def is_alive(self):
            return True

    result = snapshot(BotView(), Config(), {}, [])
    assert result["money"] == 20000
    assert result["money_read_at"] == 123456.0
    assert result["money_sync_seconds"] == 60
