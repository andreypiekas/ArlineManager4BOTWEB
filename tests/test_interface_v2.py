"""Contratos de interface: textos pt-BR, acessibilidade e comandos preservados."""
from __future__ import annotations

import ast
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from bot import BotState
from i18n import EN, set_language, t
from settings_schema import TABS

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "assets/web/index.html"


class _Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        self.tags.append((tag, props))
        if "id" in props:
            self.ids.append(props["id"])


def test_painel_preserva_ids_e_operacoes_da_api():
    texto = WEB.read_text(encoding="utf-8")
    parser = _Ids()
    parser.feed(texto)
    obrigatorios = {
        "btnStart", "btnStop", "btnNow", "pill", "state", "dry", "next",
        "profile", "kMoney", "kRep", "kFuel", "kCo2", "kFleet", "kGoal",
        "bRep", "bFuel", "bCo2", "bGoal", "tagFilter", "tabs", "panel",
        "log", "updated",
    }
    assert obrigatorios.issubset(parser.ids)
    assert len(parser.ids) == len(set(parser.ids)), "ID duplicado no painel"
    for caminho in ("/api/status", "/api/log?since=", "/api/settings", "/api/control"):
        assert caminho in texto
    for acao in ('"start"', '"stop"', '"run_now"'):
        assert acao in texto


def test_nova_identidade_visual_responsiva_e_sem_dependencias_externas():
    html = WEB.read_text(encoding="utf-8")
    assert '<html lang="pt-BR">' in html
    assert "TORRE DE" in html and "CONTROLE." in html
    assert "FLIGHT<br>OPERATIONS" in html
    assert "--signal: #c8fc79" in html
    assert "@media (max-width: 800px)" in html
    assert 'href="#overview"' in html and 'href="#activity"' in html
    assert 'href="#parameters"' in html
    assert "aria-live" in html and ":focus-visible" in html
    assert "https://fonts.googleapis.com" not in html
    assert "<script src=" not in html


def test_javascript_eh_sintaticamente_valido(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js não instalado no executor")
    html = WEB.read_text(encoding="utf-8")
    assert html.count("<script>") == 1 and html.count("</script>") == 1
    codigo = html.split("<script>", 1)[1].split("</script>", 1)[0]
    caminho = tmp_path / "web.js"
    caminho.write_text(codigo, encoding="utf-8")
    ver = subprocess.run([node, "--check", str(caminho)], capture_output=True, text=True, check=False)
    assert ver.returncode == 0, ver.stderr


def test_desktop_usando_design_de_operacoes():
    app = (ROOT / "src/app.py").read_text(encoding="utf-8")
    theme = (ROOT / "assets/theme.json").read_text(encoding="utf-8")
    assert 'text="AM / 04"' in app
    assert "01 / TELEMETRIA DA COMPANHIA" in app
    assert "#c8fc79" in theme and "#0b1014" in theme
    assert "banner = ctk.CTkImage" not in app


def test_estados_e_abas_partem_do_portugues():
    assert [nome for nome, *_ in TABS] == ["Mercado", "Frota", "Rotas", "Aeronaves", "Opções", "Telegram"]
    assert BotState.STARTING.value == "Abrindo navegador"
    assert BotState.LOGGING_IN.value == "Fazendo login"
    assert BotState.RUNNING.value == "Em execução"
    assert BotState.ERROR.value == "Erro"
    set_language("pt_BR")
    assert t("Frota") == "Frota"
    assert t("Rotas") == "Rotas"
    assert t("Salvar configurações") == "Salvar configurações"
    set_language("en")
    assert t("Frota") == "Fleet"
    assert t("Rotas") == "Routes"
    assert t("Aeronaves") == "Aircraft"
    assert t("Opções") == "Options"
    assert t("Salvar configurações") == "Save settings"
    assert t(BotState.RUNNING.value) == "Running"
    set_language("pt_BR")


def test_chaves_inglesas_sao_portuguesas_e_sem_duplicatas():
    assert len(EN) >= 130
    assert "Frota" in EN and "Aeronaves" in EN
    for proibido in ("Guardar ajustes", "Flota", "Aviones", "Opciones", "Velocidad"):
        assert proibido not in EN


def test_log_e_telegram_nao_exibem_as_mensagens_espanholas_identificadas():
    proibidos = {
        "src/fleet.py": ("Ruta creada",),
        "src/seats.py": ("velocidad +10 %",),
        "src/bot.py": ("Abriendo navegador", "Iniciando sesión", "En marcha", "Detalles:"),
        "src/app.py": ("Tendrá su propia cuenta", "No encuentro ese modelo"),
        "src/web.py": ("Iniciando el bot", "El bot ya está", "Guardado."),
    }
    for path, patterns in proibidos.items():
        text = (ROOT / path).read_text(encoding="utf-8")
        for pattern in patterns:
            assert pattern not in text, f"{path}: {pattern}"


def test_todas_as_chamadas_diretas_a_t_utilizam_originais_portugueses():
    termos_espanhois = re.compile(
        r"\b(?:aviones|flota|opciones|guardar|nuevo|contraseña|correo|"
        r"tendrá|asientos|no encuentro|fichero|revisando|revisión|"
        r"sin datos|en marcha|velocidad|ruta creada|despegar)\b",
        re.IGNORECASE,
    )
    for path in (ROOT / "src").glob("*.py"):
        if path.name == "i18n.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    texto = node.args[0].value
                    assert not termos_espanhois.search(texto), f"{path.name}: {texto}"
