"""Parâmetros de rotas têm categoria exclusiva, preservando as chaves existentes."""
from __future__ import annotations

from configparser import ConfigParser

from conftest import ROOT
from i18n import set_language, t
from settings_schema import (
    ALL_FIELDS, ALL_SWITCHES, FLEET_FIELDS, FLEET_SWITCHES,
    OPTION_SWITCHES, ROUTE_FIELDS, ROUTE_SWITCHES, TABS,
)


ROUTE_NUMBERS = {
    "route_max_distance", "route_max_distance_big",
    "route_min_runway", "route_min_profit_gain_pct",
    "route_analysis_per_cycle",
}
ROUTE_OPTIONS = {
    "auto_route", "analyze_duplicate_routes", "allow_duplicate_routes",
    "block_duplicate_departures", "selective_depart", "experimental_id_batch_depart",
}


def test_route_settings_have_their_own_tab_and_are_not_duplicated():
    names = [name for name, *_ in TABS]
    assert names == ["Mercado", "Frota", "Rotas", "Aeronaves", "Opções", "Telegram"]
    route = next(tab for tab in TABS if tab[0] == "Rotas")
    assert route[1] == "🧭"
    assert route[2] is ROUTE_FIELDS
    assert route[3] is ROUTE_SWITCHES
    assert set(key for key, _ in route[2]) == ROUTE_NUMBERS
    assert set(key for key, _ in route[3]) == ROUTE_OPTIONS

    numeric_keys = [key for key, _ in ALL_FIELDS]
    option_keys = [key for key, _ in ALL_SWITCHES]
    assert len(numeric_keys) == len(set(numeric_keys))
    assert len(option_keys) == len(set(option_keys))
    assert not ROUTE_NUMBERS.intersection(key for key, _ in FLEET_FIELDS)
    assert not ROUTE_OPTIONS.intersection(key for key, _ in FLEET_SWITCHES)
    assert not ROUTE_OPTIONS.intersection(key for key, _ in OPTION_SWITCHES)
    assert "fleet_actions_per_cycle" in {key for key, _ in FLEET_FIELDS}
    assert "auto_depart" in {key for key, _ in OPTION_SWITCHES}


def test_defaults_and_existing_saved_values_use_the_same_ini_keys():
    ini = ConfigParser(interpolation=None)
    assert ini.read(ROOT / "config/defaults.ini", encoding="utf-8")
    assert ROUTE_NUMBERS <= set(ini.options("settings"))
    assert ROUTE_OPTIONS <= set(ini.options("options"))
    assert ini.getboolean("options", "auto_route") is True
    assert ini.getboolean("options", "analyze_duplicate_routes") is True
    assert ini.getboolean("options", "allow_duplicate_routes") is False
    assert ini.getboolean("options", "experimental_id_batch_depart") is False
    assert ini.getint("settings", "route_analysis_per_cycle") == 5


def test_web_and_desktop_use_one_shared_route_schema():
    root = ROOT
    app = (root / "src/app.py").read_text(encoding="utf-8")
    web = (root / "src/web.py").read_text(encoding="utf-8")
    html = (root / "assets/web/index.html").read_text(encoding="utf-8")
    assert 'routes = tab("Rotas")' in app
    assert "ROUTE_FIELDS, ROUTE_SWITCHES" in app
    assert "for name, icon, fields, switches in TABS:" in web
    assert 'tab.key === "Rotas"' in html
    assert "Estratégia e segurança de rotas" in html
    assert "Limites e rentabilidade" in html
    # A switch is saved immediately and a numeric value via the Save action.
    assert 'api("/api/settings", {options: {[s.key]: enabled}})' in html
    assert 'const body = {settings: {}, text: {}};' in html
    assert 'const pendingDrafts = new Map();' in html


def test_route_category_and_labels_translate_without_altering_setting_ids():
    set_language("pt_BR")
    try:
        assert t("Rotas") == "Rotas"
        assert t("Estratégia e segurança de rotas") == "Estratégia e segurança de rotas"
        set_language("en")
        assert t("Rotas") == "Routes"
        assert t("Estratégia e segurança de rotas") == "Route strategy and safeguards"
        assert t("Limites e rentabilidade") == "Limits and profitability"
    finally:
        set_language("pt_BR")
