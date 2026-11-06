"""Brazilian Portuguese interface regression tests."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from i18n import LANGUAGES, language, set_language, t, tip
from economy import AUTO_GOAL_LABEL, is_auto_goal


def test_pt_br_is_default_and_spanish_is_not_available():
    assert list(LANGUAGES) == ["pt_BR", "en"]
    assert set_language("es") == "pt_BR"
    assert language() == "pt_BR"


def test_interface_and_help_in_portuguese():
    set_language("pt_BR")
    assert t("Guardar ajustes") == "Salvar configurações"
    assert t("Flota") == "Frota"
    assert "perfil" in tip("profile").lower()
    assert t(AUTO_GOAL_LABEL) == "Automático (progressão)"
    assert is_auto_goal(AUTO_GOAL_LABEL)


def test_english_option_still_works():
    set_language("en")
    assert t("Guardar ajustes") == "Save settings"
    assert t(AUTO_GOAL_LABEL) == "Automatic (ladder)"
    set_language("pt_BR")


def test_web_document_declares_pt_br():
    html = (Path(__file__).resolve().parents[1] / "assets/web/index.html").read_text(encoding="utf-8")
    assert '<html lang="pt-BR">' in html
    assert 'let LANG = "pt_BR"' in html
