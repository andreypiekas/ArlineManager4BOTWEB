"""Testa filtros por categoria sem enviar mensagens reais nem operar o jogo."""
from __future__ import annotations

import ast
from configparser import ConfigParser
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot import Bot
from i18n import set_language, t
from settings_schema import ALL_FIELDS, ALL_SWITCHES, TABS, TELEGRAM_FIELDS, TELEGRAM_SWITCHES
from web import WebDashboard

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {
    "errors", "status", "daily", "departures", "fuel", "co2", "routes", "aircraft",
    "maintenance", "hangar", "workshop", "marketing", "checklist", "simulation",
}


class FakeConfig:
    def __init__(self, *, master=True, off=()):
        self.flags = {"telegram": master, **{f"telegram_{k}": False for k in off}}
        self.profile = SimpleNamespace(is_main=True, label="principal")
        self.values = {}
        self.saves = 0

    def get_bool(self, section, key, fallback=False):
        return self.flags.get(key, fallback)

    def get_int(self, section, key, fallback=0):
        return fallback

    def get(self, section, key, fallback=""):
        return self.values.get(key, fallback)

    def set(self, section, key, value):
        if section == "options":
            self.flags[key] = value == "on"
        else:
            self.values[key] = value

    def save(self):
        self.saves += 1


class FakeTelegram:
    enabled = True

    def __init__(self):
        self.calls = []

    def send(self, text, silent=False):
        self.calls.append((text, silent))


def bot_with_flags(*, master=True, off=()):
    bot = Bot.__new__(Bot)
    bot.config = FakeConfig(master=master, off=off)
    bot.telegram = FakeTelegram()
    return bot


@pytest.mark.parametrize("category", sorted(CATEGORIES))
def test_categoria_desativada_nao_enfileira(category):
    bot = bot_with_flags(off=[category])
    assert bot.notify("Mensagem filtrada", category=category) is False
    assert bot.telegram.calls == []
    other = "errors" if category != "errors" else "fuel"
    assert bot.notify("Mensagem permitida", category=other) is True
    assert bot.telegram.calls == [("Mensagem permitida", False)]


def test_chave_geral_bloqueia_todos_os_envios():
    bot = bot_with_flags(master=False)
    for category in CATEGORIES:
        assert not bot.notify("Não enviar", category=category)
    assert not bot.notify("Envio legado")
    assert bot.telegram.calls == []


def test_filtros_preservam_mensagens_legadas_e_modo_silencioso():
    bot = bot_with_flags()
    assert bot.notify("Texto legado", silent=True)
    assert bot.notify("🛫 Rota criada", silent=False, category="routes")
    assert bot.telegram.calls == [("Texto legado", True), ("🛫 Rota criada", False)]


def test_mensagens_de_perfis_diferentes_sao_identificadas():
    bot = bot_with_flags()
    bot.config.profile = SimpleNamespace(is_main=False, label="Companhia X")
    assert bot.notify("<b>Compra</b>", category="fuel")
    assert bot.telegram.calls == [("[Companhia X] <b>Compra</b>", False)]


def test_telegram_sem_credenciais_nao_enfileira():
    bot = bot_with_flags()
    bot.telegram.enabled = False
    assert not bot.notify("Teste", category="errors")
    assert bot.telegram.calls == []


def test_todas_as_categorias_sao_exibidas_na_aba_telegram():
    tabs = [name for name, *_ in TABS]
    assert tabs == ["Mercado", "Frota", "Rotas", "Aeronaves", "Opções", "Telegram"]
    switches = dict(TELEGRAM_SWITCHES)
    assert len(switches) == 15
    assert set(switches) == {"telegram"} | {f"telegram_{c}" for c in CATEGORIES}
    assert TELEGRAM_FIELDS == [("summary_hour", "Horário do resumo diário (0-23)")]
    assert "summary_hour" in dict(ALL_FIELDS)
    assert set(switches).issubset(dict(ALL_SWITCHES))


def test_default_de_instalacoes_anteriores_preservado():
    ini = ConfigParser()
    ini.read(ROOT / "config/defaults.ini", encoding="utf-8")
    for key, _label in TELEGRAM_SWITCHES:
        assert ini.getboolean("options", key)
    assert ini.get("settings", "summary_hour") == "9"


def test_alteracoes_individuais_sao_salvas_sem_afetar_demais_categorias():
    cfg = FakeConfig()
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.cfg = cfg
    dashboard.bot = SimpleNamespace(marketing_next_check=0.0)
    ok, _ = dashboard.update_settings({"options": {"telegram_fuel": False}})
    assert ok
    assert cfg.flags["telegram_fuel"] is False
    assert cfg.get_bool("options", "telegram_errors", True)
    assert cfg.get_bool("options", "telegram_co2", True)
    assert cfg.saves == 1


def test_todas_as_chamadas_operacionais_informam_sua_categoria():
    for file in ("bot.py", "fleet.py", "maintenance.py", "seats.py",
                 "marketing.py", "checklist.py"):
        path = ROOT / "src" / file
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr == "notify":
                assert any(kw.arg == "category" for kw in node.keywords), (
                    f"{file}:{node.lineno} notificação sem categoria"
                )


def test_telegram_pode_ser_testado_sem_expor_token(monkeypatch):
    import notify

    class Client:
        def __init__(self, token, chat):
            assert (token, chat) == ("token-test", "chat-test")

        def send_now(self, message):
            assert "Teste AM/04" in message
            return True, "enviado"

    monkeypatch.setattr(notify, "Telegram", Client)
    cfg = FakeConfig()
    cfg.reload_secrets = lambda: None
    cfg.telegram = ("token-test", "chat-test")
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.cfg = cfg
    ok, msg = dashboard.control("telegram_test")
    assert ok
    assert "Telegram" in msg
    assert "token-test" not in msg


def test_sem_credenciais_teste_aponta_configuracao(monkeypatch):
    cfg = FakeConfig()
    cfg.reload_secrets = lambda: None
    cfg.telegram = ("", "")
    dashboard = WebDashboard.__new__(WebDashboard)
    dashboard.cfg = cfg
    ok, msg = dashboard.control("telegram_test")
    assert not ok
    assert "secrets.ini" in msg


def test_filtros_na_interface_web_e_mensagens_em_ingles():
    html = (ROOT / "assets/web/index.html").read_text(encoding="utf-8")
    assert 'tab.key === "Telegram"' in html
    assert 'className = "telegram-switch-grid"' in html
    assert 'api("/api/control", {action: "telegram_test"})' in html
    assert 'switchRows.appendChild(row)' in html
    set_language("en")
    assert t("Erros e interrupções") == "Errors and interruptions"
    assert t("Decolagens") == "Departures"
    set_language("pt_BR")
