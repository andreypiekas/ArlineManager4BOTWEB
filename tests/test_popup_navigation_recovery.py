"""Popup navigation should recover an inert menu without retrying transactions."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from selenium.common.exceptions import TimeoutException

import bot as bot_module
from bot import Bot


class FakeWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, predicate):
        if predicate(self.driver):
            return True
        raise TimeoutException("popup not ready")


def make_bot(monkeypatch, *, menu_present: bool, menu_opens: bool, direct_opens: bool):
    monkeypatch.setattr(bot_module, "WebDriverWait", FakeWait)
    state = {"ready": False, "menu": 0, "direct": 0, "close": 0}
    bot = Bot.__new__(Bot)
    bot.driver = SimpleNamespace()
    bot.config = SimpleNamespace(get=lambda section, key: "test_xpath")
    bot._stop = SimpleNamespace(wait=lambda seconds: False)
    bot.pause = lambda: None
    bot._popup_ready = lambda: state["ready"]

    def click():
        state["menu"] += 1
        state["ready"] = menu_opens

    bot._find = lambda xpath, timeout=3: SimpleNamespace(click=click) if menu_present else None

    def js(script, *args):
        if "window.popup(" in script:
            state["direct"] += 1
            state["ready"] = direct_opens
            return True
        if "innerHTML = ''" in script:
            state["ready"] = False
        return None

    bot.js = js

    def close_popup(quiet=True):
        state["close"] += 1

    bot.close_popup = close_popup
    monkeypatch.setattr(bot_module, "summarize_browser_state", lambda d: "dados seguros")
    return bot, state


def test_menu_succeeds_without_direct_retry(monkeypatch):
    bot, state = make_bot(monkeypatch, menu_present=True, menu_opens=True, direct_opens=True)
    bot.open_popup("fuel.php", "Fuel", "nav_fuel")
    assert state["menu"] == 1
    assert state["direct"] == 0


def test_inert_menu_uses_popup_helper(monkeypatch):
    bot, state = make_bot(monkeypatch, menu_present=True, menu_opens=False, direct_opens=True)
    bot.open_popup("maintenance_main.php", "Maintenance", "nav_maintenance")
    assert state["menu"] == 1
    assert state["direct"] == 1
    assert state["close"] == 1


def test_missing_menu_uses_popup_helper(monkeypatch):
    bot, state = make_bot(monkeypatch, menu_present=False, menu_opens=False, direct_opens=True)
    bot.open_popup("finances.php", "Finances", "nav_finances")
    assert state["direct"] == 1


def test_both_methods_fail_with_timeout(monkeypatch):
    bot, state = make_bot(monkeypatch, menu_present=True, menu_opens=False, direct_opens=False)
    with pytest.raises(TimeoutException):
        bot.open_popup("routes_main.php", "Routes", "nav_routes")
    assert state["menu"] == state["direct"] == 1


def test_no_menu_and_no_popup_reports_timeout(monkeypatch):
    bot, state = make_bot(monkeypatch, menu_present=False, menu_opens=False, direct_opens=False)
    with pytest.raises(TimeoutException):
        bot.open_popup("fuel.php", "Fuel", "nav_fuel")
    assert state["direct"] == 1
