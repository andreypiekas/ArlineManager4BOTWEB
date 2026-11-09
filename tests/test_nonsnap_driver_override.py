"""Non-Snap Chrome is an explicit, reversible service configuration."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import driver


def executable(path: Path) -> str:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return str(path)


def test_default_browser_detection_is_unchanged(monkeypatch):
    monkeypatch.delenv("AM4_CHROME_BINARY", raising=False)
    monkeypatch.delenv("AM4_CHROMEDRIVER_BINARY", raising=False)
    monkeypatch.setattr(driver, "_system_chrome", lambda: (
        "/usr/bin/chromedriver", "/usr/bin/chromium"
    ))
    assert driver._selected_chrome() == ("/usr/bin/chromedriver", "/usr/bin/chromium")


def test_requires_complete_binary_pair_and_avoids_snap_system_mixing(tmp_path, monkeypatch):
    chrome = executable(tmp_path / "chrome")
    monkeypatch.setenv("AM4_CHROME_BINARY", chrome)
    monkeypatch.delenv("AM4_CHROMEDRIVER_BINARY", raising=False)
    with pytest.raises(ValueError, match="juntos"):
        driver._selected_chrome()

    monkeypatch.delenv("AM4_CHROME_BINARY", raising=False)
    monkeypatch.setenv("AM4_CHROMEDRIVER_BINARY", chrome)
    with pytest.raises(ValueError, match="juntos"):
        driver._selected_chrome()


def test_binary_paths_require_absolute_executables(tmp_path, monkeypatch):
    chrome = executable(tmp_path / "chrome")
    chromedriver = executable(tmp_path / "chromedriver")
    monkeypatch.setenv("AM4_CHROME_BINARY", chrome)
    monkeypatch.setenv("AM4_CHROMEDRIVER_BINARY", chromedriver)
    assert driver._selected_chrome() == (chromedriver, chrome)

    monkeypatch.setenv("AM4_CHROME_BINARY", "chrome")
    with pytest.raises(ValueError, match="caminho absoluto"):
        driver._selected_chrome()

    monkeypatch.setenv("AM4_CHROME_BINARY", str(tmp_path / "inexistente"))
    with pytest.raises(ValueError, match="executável"):
        driver._selected_chrome()


def test_external_chrome_start_uses_new_profile_not_existing_snap_profile(
    tmp_path, monkeypatch,
):
    chrome = executable(tmp_path / "chrome")
    chromedriver = executable(tmp_path / "chromedriver")
    profile = tmp_path / "isolated-chrome"
    old_session = tmp_path / "snap-session"
    old_session.mkdir()
    (old_session / "KEEP").write_text("unchanged", encoding="utf-8")
    monkeypatch.setenv("AM4_CHROME_BINARY", chrome)
    monkeypatch.setenv("AM4_CHROMEDRIVER_BINARY", chromedriver)
    monkeypatch.setenv("AM4_CHROME_PROFILE_DIR", str(profile))
    monkeypatch.setattr(driver.paths, "current", lambda: SimpleNamespace(
        data=tmp_path / "data", session=old_session,
    ))
    received = {}

    class FakeService:
        def __init__(self, executable_path, log_output):
            received["executable_path"] = executable_path
            received["log_output"] = log_output

    class FakeDriver:
        def set_page_load_timeout(self, sec):
            received["page_timeout"] = sec

        def get(self, url):
            received["url"] = url

    def fake_chrome(*, service, options):
        assert service is not None
        received["browser"] = options.binary_location
        received["arguments"] = options.arguments
        return FakeDriver()

    monkeypatch.setattr(driver, "Service", FakeService)
    monkeypatch.setattr(driver.webdriver, "Chrome", fake_chrome)
    web_driver = driver.create_driver(
        "https://www.airlinemanager.com", keep_session=True, headless=True
    )
    assert isinstance(web_driver, FakeDriver)
    assert received["browser"] == chrome
    assert received["executable_path"] == chromedriver
    assert f"--user-data-dir={profile}" in received["arguments"]
    assert "--headless=new" in received["arguments"]
    assert received["url"] == "https://www.airlinemanager.com"
    assert received["log_output"].closed
    assert profile.is_dir()
    assert (old_session / "KEEP").read_text(encoding="utf-8") == "unchanged"


def test_profile_override_must_be_absolute(tmp_path, monkeypatch):
    monkeypatch.setenv("AM4_CHROME_PROFILE_DIR", "relative-profile")
    monkeypatch.setattr(driver.paths, "current", lambda: SimpleNamespace(
        data=tmp_path, session=tmp_path / "session"
    ))
    with pytest.raises(ValueError, match="caminho absoluto"):
        driver.create_driver("https://example.com", keep_session=True)
