"""Repeated game popup timeouts must stop a useless retry cascade."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from selenium.common.exceptions import TimeoutException

from bot import Bot
from web_health import summarize_browser_state


def failing_action():
    raise TimeoutException("waiting for a game popup")


def test_three_consecutive_timeouts_request_supervised_recovery():
    bot = Bot.__new__(Bot)
    bot._web_timeout_streak = 0
    bot._stop = SimpleNamespace(is_set=lambda: False)
    bot.driver = SimpleNamespace(execute_script=lambda script: {
        "ready": "complete", "online": True, "popupPresent": True,
    })
    bot.close_popup = lambda quiet=True: None

    bot._guard(failing_action, "marketing")
    bot._guard(failing_action, "manutenção")
    assert bot._web_timeout_streak == 2
    with pytest.raises(RuntimeError, match="três operações seguidas"):
        bot._guard(failing_action, "decolagem")


def test_success_resets_timeout_streak():
    bot = Bot.__new__(Bot)
    bot._web_timeout_streak = 2
    bot._stop = SimpleNamespace(is_set=lambda: False)
    bot.driver = None
    bot.close_popup = lambda quiet=True: None

    bot._guard(lambda: None, "operação concluída")
    assert bot._web_timeout_streak == 0
    bot._guard(failing_action, "manutenção")
    assert bot._web_timeout_streak == 1


def test_sanitized_diagnostic_does_not_expose_unexpected_fields():
    secret = "SECRET_ACCOUNT_TOKEN_123"
    browser = SimpleNamespace(execute_script=lambda script: {
        "ready": "complete", "online": False, "popupPresent": True,
        "popupVisible": False, "popupLength": 0, "loaderCount": 1,
        "ajaxAvailable": True, "popupAvailable": False,
        "jqueryActive": 3, "privateToken": secret,
    })
    message = summarize_browser_state(browser)
    assert "online=não" in message
    assert "loaders=1" in message
    assert "requisições_jQuery=3" in message
    assert secret not in message


def test_diagnostics_fail_safely_if_driver_is_gone():
    assert "indisponível" in summarize_browser_state(None)

    def unreachable(script):
        raise ConnectionError("do not leak this sensitive local endpoint")

    browser = SimpleNamespace(execute_script=unreachable)
    assert "ConnectionError" in summarize_browser_state(browser)
    assert "sensitive" not in summarize_browser_state(browser)
