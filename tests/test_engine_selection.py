"""Motorização: nunca comprar quando a seleção não foi confirmada no jogo."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import engine_selection
import fleet
import web


def engines(*, speed=True, fuel=True, selected="1"):
    options = [
        {"label": "Trent 970", "value": "1", "selected": selected == "1",
         "speed": 905 if speed else None, "fuel": 12.1 if fuel else None, "disabled": False},
        {"label": "GP7270", "value": "2", "selected": selected == "2",
         "speed": 921 if speed else None, "fuel": 12.4 if fuel else None, "disabled": False},
        {"label": "RR Trent 972", "value": "3", "selected": selected == "3",
         "speed": 945 if speed else None, "fuel": 12.8 if fuel else None, "disabled": False},
    ]
    return [{"type": "select", "id": "acEngine", "name": "engine", "options": options}]


@pytest.mark.parametrize("pref,expected", [
    ("name:Trent 972", "RR Trent 972"),
    ("name:rr TRENT 972", "RR Trent 972"),
    ("fastest", "RR Trent 972"),
    ("economical", "Trent 970"),
])
def test_escolhe_motor_por_nome_ou_metricas_observadas(pref, expected):
    group, selected = engine_selection.choose_engine(engines(), pref)
    assert group["type"] == "select"
    assert selected.label == expected


@pytest.mark.parametrize("pref", [
    "name:", "unknown", "name:" + "x" * 76,
])
def test_preferencias_invalidas_sao_bloqueadas(pref):
    with pytest.raises(engine_selection.EngineSelectionError):
        engine_selection.validate_preference(pref)


def test_opcao_desativada_nao_pode_ser_escolhida():
    groups = engines()
    groups[0]["options"][2]["disabled"] = True
    with pytest.raises(engine_selection.EngineSelectionError):
        engine_selection.choose_engine(groups, "name:Trent 972")


def test_nome_ambiguo_impede_compra():
    with pytest.raises(engine_selection.EngineSelectionError):
        engine_selection.choose_engine(engines(), "name:Trent")


def test_velocidade_e_consumo_sem_dados_nao_sao_adivinhados():
    with pytest.raises(engine_selection.EngineSelectionError, match="velocidade"):
        engine_selection.choose_engine(engines(speed=False), "fastest")
    with pytest.raises(engine_selection.EngineSelectionError, match="consumo"):
        engine_selection.choose_engine(engines(fuel=False), "economical")


def test_nenhum_seletor_nao_faz_fallback():
    with pytest.raises(engine_selection.EngineSelectionError, match="bloqueada"):
        engine_selection.choose_engine([], "name:RR Trent 972")


def test_varios_seletores_ambiguos_bloqueiam():
    with pytest.raises(engine_selection.EngineSelectionError):
        engine_selection.choose_engine(engines() + engines(), "fastest")


def test_selecao_exata_confirmada_apos_clique():
    calls = []

    class Bot:
        dry_run = False

        def js(self, script, *args):
            calls.append(args)
            if len(args) == 3:
                return args == ("select", "acEngine", "3")
            return engines(selected="3") if len(calls) > 2 else engines()

        def pause(self, *_):
            pass

    motor = engine_selection.prepare_engine(Bot(), "name:Trent 972")
    assert motor == "RR Trent 972"
    assert calls[1] == ("select", "acEngine", "3")


def test_ausencia_de_confirmacao_bloqueia_compra():
    class Bot:
        dry_run = False

        def js(self, script, *args):
            return True if args else engines(selected="1")

        def pause(self, *_):
            pass

    with pytest.raises(engine_selection.EngineSelectionError, match="não confirmou"):
        engine_selection.prepare_engine(Bot(), "name:Trent 972")


def test_simulacao_nunca_seleciona_nem_compra():
    calls = []

    class Bot:
        dry_run = True

        def js(self, script, *args):
            calls.append(args)
            return engines()

        def pause(self, *_):
            pytest.fail("Simulação não deve aguardar após selecionar o motor")

    assert engine_selection.prepare_engine(Bot(), "name:Trent 972") == "RR Trent 972"
    assert len(calls) == 1
    assert calls[0] == ()


def test_padrao_do_jogo_preserva_comportamento_antigo():
    class Bot:
        def js(self, *_args):
            pytest.fail("Motor padrão não deve inspecionar nem alterar o navegador")

    assert engine_selection.prepare_engine(Bot(), "default") is None


def test_fluxo_de_compra_nao_aciona_confirmacao_sem_motor_verificado(monkeypatch):
    cfg = SimpleNamespace(get=lambda section, key, fallback="": (
        "name:Trent 972" if key == "engine_preference" else fallback
    ))
    called = []

    class Detail:
        def find_elements(self, *args):
            return []

    bot = SimpleNamespace(config=cfg, ajax=lambda *_args: Detail(),
                          dry_run=False, click_element=lambda *_args: called.append("click"))
    choice = fleet.AircraftModel("123", "A380-800", 15000, 940, 600, 12, 300_000_000)
    monkeypatch.setattr(engine_selection, "prepare_engine",
                        lambda _bot, _pref: (_ for _ in ()).throw(
                            engine_selection.EngineSelectionError("Sem seletor válido")))
    assert fleet.order_aircraft(bot, choice) is False
    assert called == []


def test_api_nao_salva_preferencia_invalida():
    class Cfg:
        def __init__(self):
            self.values = {}
            self.saved = False

        def set(self, section, key, value):
            self.values[key] = value

        def save(self):
            self.saved = True

    dashboard = web.WebDashboard.__new__(web.WebDashboard)
    dashboard.cfg = Cfg()
    ok, message = dashboard.update_settings({"text": {"engine_preference": "name:"}})
    assert not ok
    assert "motor" in message.lower()
    assert dashboard.cfg.values == {}
    assert not dashboard.cfg.saved


def test_api_salva_preferencia_valida():
    class Cfg:
        def __init__(self):
            self.values = {}

        def set(self, section, key, value):
            self.values[key] = value

        def save(self):
            pass

    dashboard = web.WebDashboard.__new__(web.WebDashboard)
    dashboard.cfg = Cfg()
    ok, _ = dashboard.update_settings({"text": {"engine_preference": "name:Trent 972"}})
    assert ok
    assert dashboard.cfg.values["engine_preference"] == "name:Trent 972"


def test_nova_interface_exige_confirmacao():
    from pathlib import Path

    html = (Path(__file__).resolve().parents[1] / "assets/web/index.html").read_text(encoding="utf-8")
    assert "Configuração do motor" in html
    assert "Mais rápido (dados confirmados)" in html
    assert "Menor consumo (dados confirmados)" in html
    assert "Motor específico (nome)" in html
    assert 'draftKey("text", "engine_preference")' in html
    assert "Informe o nome do motor antes de salvar." in html
