"""Seleção explícita do modelo de compra automática, sem executar o jogo."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import fleet
import web


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "assets/web/index.html").read_text(encoding="utf-8")


class FakeConfig:
    def __init__(self, *, goal_model="auto", aircraft_model="", save_for_goal=True,
                 goal_invest=False):
        self.values = {
            ("settings", "goal_model"): goal_model,
            ("settings", "aircraft_model"): aircraft_model,
        }
        self.toggles = {"save_for_goal": save_for_goal, "goal_invest": goal_invest}
        self.saves = 0

    def get(self, section, key, fallback=""):
        return self.values.get((section, key), fallback)

    def get_int(self, section, key, fallback=0):
        return fallback

    def get_bool(self, section, key, fallback=False):
        return self.toggles.get(key, fallback)

    def set(self, section, key, value):
        if section == "options":
            self.toggles[key] = value == "on"
        else:
            self.values[(section, key)] = value

    def save(self):
        self.saves += 1


def aircraft(name, price=1000, score=1):
    return SimpleNamespace(id="id-" + name, name=name, price=price, capacity=80,
                           range_km=2500, speed=800, fuel=300, score=score, profit=300)


def test_api_exibe_todos_os_modelos_do_mercado_inclusive_pequenos(monkeypatch):
    models = [
        {"name": "B737-800", "capacity": 180, "price": 90_000},
        {"name": "Cessna 172", "capacity": 4, "price": 10_000},
        {"name": "A320-200", "capacity": 150, "price": 70_000},
        {"name": "A320-200", "capacity": 150, "price": 70_000},
    ]
    monkeypatch.setattr(web, "load_market", lambda: models)
    dashboard = web.WebDashboard.__new__(web.WebDashboard)
    dashboard.cfg = FakeConfig(goal_model="A320-200")
    result = dashboard.settings()
    assert result["aircraft_options"] == ["A320-200", "B737-800", "Cessna 172"]
    assert result["goal_options"][1:] == result["aircraft_options"]
    assert result["auto_goal_label"] == result["goal_options"][0]
    selected = next(x for x in result["text"] if x["key"] == "goal_model")
    assert selected["value"] == "A320-200"


def test_api_preserva_progressao_automatica(monkeypatch):
    monkeypatch.setattr(web, "load_market", lambda: [])
    dashboard = web.WebDashboard.__new__(web.WebDashboard)
    dashboard.cfg = FakeConfig(goal_model="auto")
    result = dashboard.settings()
    assert result["aircraft_options"] == []
    selected = next(x for x in result["text"] if x["key"] == "goal_model")
    assert selected["value"] == result["auto_goal_label"]


def test_salvar_modelo_selecionado_preserva_chave_e_outras_opcoes():
    dashboard = web.WebDashboard.__new__(web.WebDashboard)
    cfg = FakeConfig(goal_model="auto", save_for_goal=True, goal_invest=False)
    dashboard.cfg = cfg
    dashboard.bot = SimpleNamespace(marketing_next_check=0.0)
    ok, _message = dashboard.update_settings({"text": {"goal_model": "B737-800"}})
    assert ok
    assert cfg.get("settings", "goal_model") == "B737-800"
    assert cfg.get_bool("options", "save_for_goal") is True
    assert cfg.get_bool("options", "goal_invest") is False
    assert cfg.saves == 1


def test_compra_com_meta_usa_modelo_selecionado(monkeypatch):
    cfg = FakeConfig(goal_model="B737-800", save_for_goal=True)
    bot = SimpleNamespace(
        config=cfg,
        open_popup=lambda *_args: None,
        ajax=lambda *_args: None,
        pause=lambda *_args: None,
        stats=lambda: SimpleNamespace(money=50_000, hangar_free=2),
    )
    models = [aircraft("Cessna 172", 1000), aircraft("B737-800", 15_000)]
    monkeypatch.setattr(fleet, "read_models", lambda _bot: models)
    monkeypatch.setattr(fleet, "score_models", lambda *_args: None)
    monkeypatch.setattr(fleet, "save_market", lambda *_args: None)
    observed = []
    monkeypatch.setattr(fleet, "save_for_goal", lambda *_args: observed.append(_args))
    fleet.buy_aircraft(bot)
    assert len(observed) == 1
    assert observed[0][2] == "B737-800"


def test_sem_meta_usa_somente_o_modelo_fixo(monkeypatch):
    cfg = FakeConfig(goal_model="auto", aircraft_model="B737-800", save_for_goal=False)
    bot = SimpleNamespace(
        config=cfg,
        open_popup=lambda *_args: None,
        ajax=lambda *_args: None,
        pause=lambda *_args: None,
        stats=lambda: SimpleNamespace(money=50_000, hangar_free=2),
    )
    models = [aircraft("Cessna 172", 1000, score=4), aircraft("B737-800", 15_000, score=1)]
    monkeypatch.setattr(fleet, "read_models", lambda _bot: models)
    monkeypatch.setattr(fleet, "score_models", lambda *_args: None)
    monkeypatch.setattr(fleet, "save_market", lambda *_args: None)
    observed = []
    monkeypatch.setattr(fleet, "order_aircraft", lambda _bot, model: observed.append(model.name))
    fleet.buy_aircraft(bot)
    assert observed == ["B737-800"]


def test_painel_oferece_modo_e_selecao_sem_comprar_ou_salvar_automaticamente():
    assert "Estratégia de compra" in HTML
    assert "Progressão automática (bot escolhe)" in HTML
    assert "Modelo específico (você escolhe)" in HTML
    assert 'goalInput.setAttribute("list", "modelOptions")' in HTML
    assert 'input.setAttribute("list", "modelOptions")' in HTML
    assert 'settings.aircraft_options' in HTML
    assert 'pendingDrafts.set(draftKey("text", "goal_model"), chosen)' in HTML
    assert 'if (inputs.some(([kind, key, input]) => kind === "text" && key === "goal_model"' in HTML
    assert "Selecione uma aeronave específica antes de salvar." in HTML
    assert "Compras intermediárias estão permitidas" in HTML


def test_desktop_possui_escolha_e_lista_sem_limite_artificial_de_assentos():
    desktop = (ROOT / "src/app.py").read_text(encoding="utf-8")
    assert 'text=t("Modelo da compra automática")' in desktop
    assert "if m.get(\"capacity\", 0) >= 100" not in desktop
    assert "def _goal_values(self)" in desktop
    assert "desative compras intermediárias." in desktop
