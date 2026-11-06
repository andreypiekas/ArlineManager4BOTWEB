"""Regressões do layout compacto da AM/04 Torre de Controle."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "assets" / "web" / "index.html"


def test_css_compacto_prioriza_os_registros_em_desktop():
    pagina = HTML.read_text(encoding="utf-8")
    css = pagina.split("/* V03: densidade operacional.", 1)[1].split("</style>", 1)[0]
    assert ".hero h1 { font-size: clamp(32px, 3.1vw, 48px)" in css
    assert ".hero { padding: 19px 0 21px;" in css
    assert ".tile { padding: 13px 13px 11px; min-height: 116px;" in css
    assert "grid-template-columns: repeat(7, minmax(0, 1fr));" in css
    assert ".tile:last-child { grid-column: span 1; }" in css
    assert ".kpis { grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px; margin-bottom: 19px; }" in css
    assert ".audit-message { margin: 9px 0 12px; min-height: 42px;" in css
    assert ".grid { grid-template-columns: minmax(0, 1fr) 264px;" in css


def test_css_se_adapta_a_monitores_intermediarios_e_celulares():
    css = HTML.read_text(encoding="utf-8").split("/* V03: densidade operacional.", 1)[1].split("</style>", 1)[0]
    assert "@media (min-width: 801px) and (max-width: 1520px)" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css
    assert "@media (max-width: 800px)" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert ".tile:first-child, .tile:last-child { grid-column: span 2; }" in css
    assert "@media (max-width: 420px)" in css
    assert ".hero h1 { font-size: 34px; }" in css


def test_compactacao_preserva_modos_e_comandos():
    html = HTML.read_text(encoding="utf-8")
    for element in ("overview", "activity", "settingsView", "parameters", "kMoney",
                    "kRep", "kFuel", "kCo2", "kFleet", "kGoal", "log",
                    "changeSummary", "saveBanner", "btnStart", "btnStop", "btnNow"):
        assert html.count(f'id="{element}"') == 1
    assert 'class="workspace settings-workspace" id="settingsView" hidden' in html
    assert 'id="parameters" aria-label="Parâmetros operacionais"' in html
    assert 'api("/api/settings", {options: {[s.key]: enabled}})' in html
    assert 'api("/api/control", {action})' in html
    assert "setInterval(tick, 2000);" in html
