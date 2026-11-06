"""Gera capturas reais da interface AM/04, sem acessar o jogo.

Uso em Linux (X11/Xvfb) ou Windows:
    python scripts/screenshots.py

Na automação:
    xvfb-run -a -s "-screen 0 1920x1200x24" python scripts/screenshots.py

As telas exibem dados de demonstração e não usam credenciais, cookies,
token, perfil real, servidor externo nem navegação ao Airline Manager.
A execução não inicia os ciclos do bot nem salva configurações.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
WEB_PORT = 8799
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402

_get = config.AppConfig.get
_get_bool = config.AppConfig.get_bool
_get_int = config.AppConfig.get_int
LOG_FILE = Path(tempfile.gettempdir()) / "am4bot-screenshots.log"
APPEARANCE = {"mode": "Dark"}


def _patched_get(self, section, key, fallback=""):
    if (section, key) == ("app", "log_file"):
        return str(LOG_FILE)
    if (section, key) == ("app", "appearance_mode"):
        return APPEARANCE["mode"]
    return _get(self, section, key, fallback)


def _patched_get_bool(self, section, key, fallback=False):
    if (section, key) == ("web", "enabled"):
        return False  # A janela desktop não inicia seu próprio painel.
    if (section, key) == ("options", "start_on_launch"):
        return False
    return _get_bool(self, section, key, fallback)


config.AppConfig.get = _patched_get
config.AppConfig.get_bool = _patched_get_bool
config.AppConfig.get_int = (
    lambda self, section, key, fallback=0:
    WEB_PORT if (section, key) == ("web", "port") else _get_int(self, section, key, fallback)
)
config.AppConfig.save = lambda self: None
config.AppConfig.credentials = property(lambda self: ("demo@example.invalid", "senha-de-exemplo"))
config.AppConfig.telegram = property(lambda self: ("000000000:DEMONSTRACAO", "000000000"))
config.AppConfig.web_token = property(lambda self: "")

SAMPLE_STATS = dict(
    money=18740005, points=140, fuel=19502400, fuel_capacity=21102000,
    fuel_price=520, fuel_buy_at=650, co2=7541000, co2_capacity=10871000,
    co2_price=111, co2_buy_at=140, fleet_size=186, inflight=174,
    parked=6, pending=6, income_day=279800, goal_price=24000000,
    hangar_free=4, hangar_capacity=191, reputation=84,
)
SAMPLE_LOG = [
    ("app", "AM/04 pronto. Painel de demonstração, sem conexão com o jogo."),
    ("bot", "Iniciando verificação da companhia aérea de demonstração…"),
    ("dinero", "Saldo: $18.740.005 | Pontos: 140 | receita líquida estimada: $279.800/dia."),
    ("vuelos", "174 aeronaves em voo; próximo pouso em 03:29."),
    ("marketing", "Reputação: 84% | 3 campanhas ativas."),
    ("mant", "Frota: 186 aeronaves | 4 vagas disponíveis no hangar."),
    ("asientos", "Oficina: aeronave de exemplo | melhoria de velocidade +10% avaliada."),
    ("fuel", "Combustível: preço $520 | limite de compra $650 | operação simulada."),
    ("co2", "CO₂: preço $111 | limite de compra $140 | operação simulada."),
    ("flota", "6 aeronaves aguardando a próxima verificação de rotas."),
    ("bot", "Próxima verificação em 4 min 31 s."),
]


def fill(bot) -> None:
    bot.update_stats(**SAMPLE_STATS, campaign_ends=int(time.time()) + 2 * 3600 + 35 * 60)
    for category, message in SAMPLE_LOG:
        logging.getLogger(f"am4bot.{category}").info(message)


def capture_window(app, dest: Path) -> None:
    """Fotografa a interface desktop real, com Win32 ou X11/Xvfb."""
    from PIL import ImageGrab

    app.lift()
    app.update_idletasks()
    app.update()
    time.sleep(0.25)
    app.update()
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        hwnd = ctypes.windll.user32.GetParent(app.winfo_id()) or app.winfo_id()
        bounds = wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            hwnd, 9, ctypes.byref(bounds), ctypes.sizeof(bounds),
        )
        bbox = (bounds.left, bounds.top, bounds.right, bounds.bottom)
        image = ImageGrab.grab(bbox=bbox, all_screens=True)
    else:
        if not os.environ.get("DISPLAY"):
            raise RuntimeError("Capturas desktop no Linux exigem DISPLAY/Xvfb.")
        x, y = app.winfo_rootx(), app.winfo_rooty()
        bbox = (x, y, x + app.winfo_width(), y + app.winfo_height())
        image = ImageGrab.grab(bbox=bbox, xdisplay=os.environ["DISPLAY"])
    image.save(dest, format="PNG", optimize=True)
    print(f"Capturada: {dest.relative_to(ROOT)} ({image.width}x{image.height})", flush=True)


def desktop_shots() -> None:
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        raise RuntimeError("Sem DISPLAY. Execute sob xvfb-run para capturar o desktop no Linux.")

    from app import App, tab_title

    # Nunca executar automações durante uma captura.
    App.start_bot = lambda self: None
    mapping = (
        ("Mercado", "mercado"),
        ("Frota", "frota"),
        ("Aeronaves", "aeronaves"),
        ("Opções", "opcoes"),
    )
    for mode, tabs in (
        ("Dark", mapping),
        ("Light", mapping[:1]),
    ):
        APPEARANCE["mode"] = mode
        app = App()
        try:
            app.geometry("1480x920+30+30")
            fill(app.bot)
            for _ in range(5):
                app.update()
                time.sleep(0.2)
            app._refresh_goal_panel()
            for tab, stem in tabs:
                app.tabs.set(tab_title(tab))
                app.update()
                time.sleep(0.2)
                suffix = "-light" if mode == "Light" else ""
                capture_window(app, OUT / f"desktop-{stem}{suffix}.png")
        finally:
            app.destroy()


def web_shots() -> None:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    from bot import Bot
    from logsetup import LogBuffer, setup_logging
    from web import WebDashboard

    cfg = config.AppConfig()
    buffer = LogBuffer()
    setup_logging(cfg, buffer)
    bot = Bot(cfg)
    bot.start = lambda: None
    web = WebDashboard(bot, cfg, buffer)
    if not web.start():
        raise RuntimeError("Servidor de demonstração não pôde iniciar; nenhuma imagem foi publicada.")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--force-device-scale-factor=1")
    options.add_argument("--window-size=1536,940")
    driver = None
    try:
        # Mantém as capturas livres da linha operacional da porta de testes.
        web.buffer = LogBuffer()
        setup_logging(cfg, web.buffer)
        fill(bot)
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 25)

        def navigate(*, mobile=False, tab=None):
            width, height = (430, 1120) if mobile else (1536, 940)
            driver.set_window_size(width, height)
            driver.get(f"http://127.0.0.1:{WEB_PORT}/")
            wait.until(lambda d: d.find_element(By.ID, "kMoney").text not in ("", "—"))
            if tab is not None:
                driver.execute_script("window.location.hash = '#parameters'")
                wait.until(lambda d: d.find_element(By.ID, "settingsView").is_displayed())
                wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#tabs button")) >= 4)
                driver.find_elements(By.CSS_SELECTOR, "#tabs button")[tab].click()
            driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.6)

        def shot(name, *, mobile=False, tab=None):
            navigate(mobile=mobile, tab=tab)
            dest = OUT / name
            if not driver.save_screenshot(str(dest)):
                raise RuntimeError(f"Falha ao salvar captura: {name}")
            print(f"Capturada: {dest.relative_to(ROOT)}", flush=True)

        shot("web-visao-geral.png")
        for index, tab in enumerate(("mercado", "frota", "aeronaves", "opcoes")):
            shot(f"web-config-{tab}.png", tab=index)
        shot("web-mobile.png", mobile=True)
        shot("web-mobile-config.png", mobile=True, tab=0)
    finally:
        if driver is not None:
            driver.quit()
        web.stop()


GENERATED = (
    "desktop-mercado.png", "desktop-frota.png", "desktop-aeronaves.png",
    "desktop-opcoes.png", "desktop-mercado-light.png",
    "web-visao-geral.png", "web-config-mercado.png", "web-config-frota.png",
    "web-config-aeronaves.png", "web-config-opcoes.png",
    "web-mobile.png", "web-mobile-config.png",
)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    desktop_shots()
    web_shots()

    faltando = [name for name in GENERATED if not (OUT / name).is_file()]
    if faltando:
        raise RuntimeError("Capturas ausentes: " + ", ".join(faltando))

    # Limpa capturas obsoletas apenas após gerar a nova série completa.
    for caminho in OUT.glob("*.png"):
        if caminho.name not in GENERATED:
            caminho.unlink()
            print(f"Removida captura antiga: {caminho.relative_to(ROOT)}", flush=True)
    print(f"Capturas AM/04 atualizadas: {len(GENERATED)} arquivos.", flush=True)


if __name__ == "__main__":
    main()
