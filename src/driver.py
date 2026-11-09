"""Chrome WebDriver factory.

Selenium >= 4.6 ships Selenium Manager, which downloads the chromedriver that matches the installed
Chrome. Google publishes no chromedriver for ARM Linux (Raspberry Pi), so there the system Chromium and
its distribution chromedriver are used instead (``sudo apt install chromium chromium-driver``).
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

import paths

log = logging.getLogger("am4bot.app")

_LINUX_BROWSERS = ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome")


def _system_chrome() -> tuple[Optional[str], Optional[str]]:
    """(chromedriver, browser) installed by the Linux distribution, or (None, None) to let Selenium Manager decide."""
    if os.name == "nt":
        return None, None
    driver = shutil.which("chromedriver")
    browser = next((path for path in _LINUX_BROWSERS if Path(path).exists()), None)
    return (driver, browser) if driver and browser else (None, None)


def _selected_chrome() -> tuple[Optional[str], Optional[str]]:
    """Allow an *opt-in* non-Snap browser/driver pair for systemd deployments.

    Both binaries must be explicitly supplied. No automatic switch or
    package installation occurs, and the old default remains unchanged.
    """
    chosen_driver = os.environ.get("AM4_CHROMEDRIVER_BINARY", "").strip()
    chosen_browser = os.environ.get("AM4_CHROME_BINARY", "").strip()
    if not chosen_driver and not chosen_browser:
        return _system_chrome()
    if not chosen_driver or not chosen_browser:
        raise ValueError(
            "Defina AM4_CHROME_BINARY e AM4_CHROMEDRIVER_BINARY juntos; "
            "não misture ChromeDriver Snap com navegador não-Snap."
        )
    binaries = []
    for label, raw in (
        ("AM4_CHROMEDRIVER_BINARY", chosen_driver),
        ("AM4_CHROME_BINARY", chosen_browser),
    ):
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute() or not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise ValueError(
                f"{label}: executável não encontrado ou sem permissão; "
                "informe um caminho absoluto válido."
            )
        binaries.append(str(candidate))
    log.info(
        "Navegador configurado explicitamente: ChromeDriver=%s; Chrome=%s.",
        binaries[0], binaries[1],
    )
    return binaries[0], binaries[1]


def _open_driver_log():
    """Captura stderr/stdout do ChromeDriver, incluindo erros do wrapper Snap.

    O arquivo é privado (0600) e separado por perfil.
    """
    path = paths.current().data / "logs" / "chromedriver.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        fd = os.open(path, flags, 0o600)
        try:
            if os.name != "nt":
                os.fchmod(fd, 0o600)
            return os.fdopen(fd, "ab", buffering=0), path
        except BaseException:
            os.close(fd)
            raise
    except OSError as exc:
        log.warning("Não foi possível abrir o log do ChromeDriver (%s): %s.", path, exc)
        return None, path


def create_driver(url: str, keep_session: bool = False, headless: bool = False) -> WebDriver:
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument("--headless=new")

    if keep_session:
        # Dedicated Chrome profile inside the project (git-ignored), one per bot profile, so the
        # "remember me" cookie survives between runs and two airlines never share a browser.
        session_override = os.environ.get("AM4_CHROME_PROFILE_DIR", "").strip()
        session = Path(session_override).expanduser() if session_override else paths.current().session
        if session_override and not session.is_absolute():
            raise ValueError("AM4_CHROME_PROFILE_DIR deve ser um caminho absoluto.")
        session.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={session.resolve()}")

    chromedriver, browser = _selected_chrome()
    if chromedriver:
        options.binary_location = browser
        log.debug("Usando ChromeDriver do sistema: %s; navegador: %s.", chromedriver, browser)
        output, log_path = _open_driver_log()
        try:
            service = Service(executable_path=chromedriver, log_output=output)
            try:
                driver = webdriver.Chrome(service=service, options=options)
            except Exception:
                log.error(
                    "Falha ao iniciar ChromeDriver (%s). Confira %s e "
                    "'sudo journalctl -k -n 100 --no-pager'. "
                    "No Ubuntu Snap, teste 'chromedriver --version' com o usuário do serviço.",
                    chromedriver, log_path,
                )
                raise
        finally:
            # O processo filho mantém seu descritor; não deixar o arquivo aberto
            # no processo Python durante toda a execução.
            if output is not None:
                output.close()
    else:
        driver = webdriver.Chrome(options=options)
    try:
        driver.set_page_load_timeout(60)
        driver.get(url)
    except BaseException:
        # Nobody else holds this driver yet: an orphan Chrome would keep the profile folder locked and
        # every automatic restart would then fail with "user data directory is already in use".
        try:
            driver.quit()
        except Exception:  # noqa: BLE001 - the original error is the one worth reporting
            pass
        raise
    return driver
