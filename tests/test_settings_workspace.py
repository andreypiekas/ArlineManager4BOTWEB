"""Regressões da separação de configurações do painel de operações."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "assets/web/index.html"


class Estrutura(HTMLParser):
    """Registra quais IDs estão contidos em cada workspace HTML."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.parents = {}
        self.attrs = {}

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        element_id = props.get("id")
        if element_id:
            assert element_id not in self.parents, f"ID duplicado: {element_id}"
            self.parents[element_id] = [item_id for _, item_id in self.stack if item_id]
            self.attrs[element_id] = props
        if tag not in self.VOID:
            self.stack.append((tag, element_id))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def estrutura():
    parser = Estrutura()
    parser.feed(HTML.read_text(encoding="utf-8"))
    return parser


def test_operacoes_e_configuracoes_em_telas_independentes():
    page = estrutura()
    assert "overview" in page.parents["activity"]
    assert "overview" in page.parents["changeSummary"]
    assert "settingsView" in page.parents["parameters"]
    assert "settingsView" in page.parents["panel"]
    assert "settingsView" in page.parents["tabs"]
    assert "settingsView" in page.parents["saveBanner"]
    assert "settingsView" in page.parents["msg"]
    assert "overview" not in page.parents["parameters"]
    assert "hidden" in page.attrs["settingsView"]


def test_resumo_de_alteracoes_substitui_formulario_no_painel():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="changeSummary" aria-live="polite"' in html
    assert 'href="#parameters" data-t="Abrir configurações"' in html
    assert 'class="settings-back"' in html
    assert 'role="status" aria-live="polite"' in html
    assert 'id="saveBanner" data-state="idle"' in html
    assert "Alteração salva: {x}" in html
    assert "Alteração pendente: {x}" in html
    assert "Falha ao salvar. Confira sua conexão e tente novamente." in html
    assert 'summary.removeAttribute("data-t")' in html


def test_navegacao_por_fragmento_mantem_o_dashboard_ativo():
    html = HTML.read_text(encoding="utf-8")
    assert 'target === "#parameters"' in html
    assert '$("overview").hidden = isSettings;' in html
    assert '$("settingsView").hidden = !isSettings;' in html
    assert 'target === "#activity"' in html
    assert 'window.addEventListener("hashchange", activateWorkspaceFromHash)' in html
    assert '"aria-current", "page"' in html
    assert '.nav-list { display: flex; flex-wrap: wrap;' in html  # acessível no celular
    assert 'href="#overview" class="settings-back"' in html


def test_salvamento_automatico_e_manual_preservados():
    html = HTML.read_text(encoding="utf-8")
    # Chaves e rota do backend não foram renomeadas.
    assert 'api("/api/settings", {options: {[s.key]: enabled}})' in html
    assert 'const body = {settings: {}, text: {}};' in html
    assert 'const result = await api("/api/settings", body);' in html
    assert 'const pendingDrafts = new Map();' in html
    assert 'pendingDrafts.get(draftKey("settings", s.key)) ?? s.value' in html
    assert 'pendingDrafts.get(draftKey("text", s.key)) ?? (s.value || "")' in html
    assert 'pendingDrafts.delete(draftKey(kind, key))' in html
    assert 'save.disabled = true' in html
    assert 'input.disabled = true' in html
    assert 'input.checked = !enabled' in html  # restaura em falha


def test_textos_de_status_sao_traduziveis_para_ingles():
    html = HTML.read_text(encoding="utf-8")
    esperado = (
        '"Alterações": "Changes"',
        '"Abrir configurações": "Open settings"',
        '"STATUS DAS ALTERAÇÕES": "CHANGE STATUS"',
        '"Alteração salva: {x}": "Saved: {x}"',
        '"Salvar alterações": "Save changes"',
    )
    for texto in esperado:
        assert texto in html
