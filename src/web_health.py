"""Sanitized browser/frontend diagnostics, safe to include in support logs.

Never extract the account name, cookies, DOM text, navigation query strings or
page source: those may contain private account information.
"""
from __future__ import annotations


_HEALTH_JS = """
const el = document.getElementById('popContent');
const ready = document.readyState;
return {
    ready: ready,
    online: navigator.onLine,
    popupPresent: !!el,
    popupVisible: !!el && el.getClientRects().length > 0,
    popupLength: el ? el.innerHTML.trim().length : 0,
    loaderCount: el ? el.querySelectorAll("img[src*='loader']").length : 0,
    ajaxAvailable: typeof window.Ajax === 'function',
    popupAvailable: typeof window.popup === 'function',
    jqueryActive: window.jQuery ? window.jQuery.active : null
};
"""


def summarize_browser_state(driver: object) -> str:
    """Return only whitelisted booleans/numbers, even if the driver misbehaves."""
    if driver is None:
        return "navegador indisponível"
    try:
        data = driver.execute_script(_HEALTH_JS)
    except Exception as exc:  # noqa: BLE001 - this is best-effort debugging
        return f"diagnóstico indisponível ({type(exc).__name__})"
    if not isinstance(data, dict):
        return "diagnóstico indisponível (resposta inválida)"

    ready = data.get("ready")
    if ready not in ("loading", "interactive", "complete"):
        ready = "desconhecido"

    def flag(key: str) -> str:
        value = data.get(key)
        return "sim" if value is True else "não" if value is False else "?"

    def count(key: str) -> str:
        value = data.get(key)
        return str(max(0, min(value, 1000000))) if type(value) is int else "?"

    return (
        f"documento={ready}; online={flag('online')}; "
        f"janela_existe={flag('popupPresent')}; "
        f"janela_visível={flag('popupVisible')}; "
        f"html_janela={count('popupLength')}; "
        f"loaders={count('loaderCount')}; "
        f"Ajax={flag('ajaxAvailable')}; "
        f"popupJS={flag('popupAvailable')}; "
        f"requisições_jQuery={count('jqueryActive')}"
    )
