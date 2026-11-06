"""Verifica traduções visíveis sem renomear chaves internas ou seletores."""
from pathlib import Path

from helpers import LEVEL_STYLES, LOG_TAGS
from i18n import set_language, t
from settings_schema import ALL_FIELDS, ALL_SWITCHES, TABS

ROOT = Path(__file__).resolve().parents[1]


def test_categorias_operacionais_em_portugues():
    esperado = {
        "dinero": "DINHEIRO",
        "vuelos": "VOOS",
        "fuel": "COMBUSTÍVEL",
        "mant": "MANUTENÇÃO",
        "flota": "FROTA",
        "rutas": "ROTAS",
        "aviones": "AERONAVES",
        "asientos": "ASSENTOS",
    }
    for chave, rotulo in esperado.items():
        assert LOG_TAGS[chave][0] == rotulo
    assert LEVEL_STYLES["ERROR"][0] == "ERRO"
    assert LEVEL_STYLES["CRITICAL"][0] == "ERRO"


def test_painel_web_traduzido_com_ingles_opcional():
    html = (ROOT / "assets/web/index.html").read_text(encoding="utf-8")
    assert '<html lang="pt-BR">' in html
    assert 'data-t="⛽ Combustível"' in html
    assert 'data-t="🌿 CO₂"' in html
    assert '"⛽ Combustível": "⛽ Fuel"' in html
    assert 'let LANG = "pt_BR"' in html


def test_rotulos_desktop_em_portugues():
    set_language("pt_BR")
    exemplos = {
        "Flota": "Frota",
        "Aviones": "Aeronaves",
        "Opciones": "Opções",
        "Guardar ajustes": "Salvar configurações",
        "Nuevo perfil": "Novo perfil",
        "Sin datos todavía": "Ainda sem dados",
        "Probar Telegram": "Testar Telegram",
    }
    for espanhol, portugues in exemplos.items():
        assert t(espanhol) == portugues
    for _, _, fields, switches in TABS:
        for _, rotulo in fields + switches:
            assert rotulo.strip()
            assert not any(x in rotulo.casefold() for x in ("flota", "aviones", "guardar ajustes"))
    assert len(ALL_FIELDS) > 10
    assert len(ALL_SWITCHES) > 10

    set_language("en")
    assert t("Flota") == "Fleet"
    assert t("Comprar combustível") == "Buy fuel"
    set_language("pt_BR")


def test_mensagens_operacionais_sem_espanhol_residual():
    obsoletas = {
        "src/bot.py": ["comprobar el tutorial", "gestionar la flota", "No encuentro el panel", "Falta el selector"],
        "src/maintenance.py": ["hasta el check", "Planificado:"],
        "src/seats.py": ["no he podido leer los asientos", "otros asientos ni con mejoras",
                         "cobra $", "mejoras "],
        "src/checklist.py": ["No he podido leer el checklist", "tarea completada"],
        "src/paths.py": ["El perfil «"],
        "src/supervisor.py": ["Reinicio automático en", "Reiniciando el bot"],
        "scripts/web.ps1": ["Pulsa Enter para cerrar", "ya esta en marcha"],
        "scripts/web_parar.ps1": ["El panel no ha respondido", "No ha terminado a tiempo"],
    }
    for caminho, trechos in obsoletas.items():
        texto = (ROOT / caminho).read_text(encoding="utf-8")
        for trecho in trechos:
            assert trecho not in texto, f"Texto espanhol em {caminho}: {trecho}"


def test_documentacao_publica_em_portugues():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Funcionalidades" in readme
    assert "## Instalação fácil no Raspberry Pi OS e Ubuntu" in readme
    assert "## Features" not in readme
    assert "Made with ❤️ in Spain" not in readme
    assert "## Configuration" not in readme
    assert "## Arquivos de configuração" in readme
