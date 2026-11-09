"""ChromeDriver crashes must be diagnosed and restarted without a rapid failure loop."""
from __future__ import annotations

from types import SimpleNamespace

import browser_health
from bot import Bot, BotState
from supervisor import AutoRestart, RESTART_DELAY_MIN, RESTART_STABLE_SECONDS


def test_transport_connection_refused_is_not_a_normal_page_timeout():
    raw = (
        "HTTPConnectionPool(host='localhost', port=35889): Max retries exceeded "
        "with url: /session/secret/refresh (Caused by NewConnectionError: "
        "[Errno 111] Connection refused)"
    )
    error = ConnectionError(raw)
    assert browser_health.is_driver_disconnected(error)
    message = browser_health.user_facing_error(error)
    assert "ChromeDriver desconectou" in message
    assert "secret" not in message
    assert "35889" not in message
    assert not browser_health.is_driver_disconnected(TimeoutError("page load timeout"))
    assert browser_health.user_facing_error(RuntimeError("erro comum")) == "erro comum"


def test_chromedriver_health_reports_exit_code_and_available_memory_without_secrets(monkeypatch):
    monkeypatch.setattr(browser_health, "_mem_available_mib", lambda: "812 MiB")
    process = SimpleNamespace(pid=123, poll=lambda: -9)
    driver = SimpleNamespace(service=SimpleNamespace(process=process))
    status = browser_health.driver_health_details(driver)
    assert "PID ChromeDriver=123" in status
    assert "encerrado (código -9)" in status
    assert "812 MiB" in status
    assert "causa do encerramento ainda não confirmada" in status
    assert "PID ChromeDriver=?" in browser_health.driver_health_details(None)


def test_driver_shutdown_ignores_urllib3_or_os_error_after_crash():
    called = []

    class LostDriver:
        def quit(self):
            called.append(True)
            raise ConnectionError("HTTPConnectionPool(host='localhost'): connection refused")

    bot = Bot.__new__(Bot)
    bot.driver = LostDriver()
    bot._quit_driver()
    assert called == [True]
    assert bot.driver is None


def test_supervisor_does_not_reset_exponential_backoff_after_short_run(monkeypatch):
    import supervisor

    moment = [1000.0]
    monkeypatch.setattr(supervisor.time, "time", lambda: moment[0])
    restart = AutoRestart()
    assert not restart.tick(False, BotState.ERROR, True)
    assert restart.restart_at == 1000.0 + RESTART_DELAY_MIN
    moment[0] = 1120.0
    assert restart.tick(False, BotState.ERROR, True)
    assert restart.delay == 240

    # Browser starts, runs for 45 seconds, and dies again. The next restart
    # should NOT be scheduled after the original two-minute delay.
    moment[0] = 1121.0
    assert not restart.tick(True, BotState.STARTING, True)
    moment[0] = 1125.0
    assert not restart.tick(True, BotState.RUNNING, True)
    moment[0] = 1170.0
    assert not restart.tick(True, BotState.RUNNING, True)
    assert restart.delay == 240
    moment[0] = 1171.0
    assert not restart.tick(False, BotState.ERROR, True)
    assert restart.restart_at == 1411.0
    moment[0] = 1411.0
    assert restart.tick(False, BotState.ERROR, True)
    assert restart.delay == 480


def test_supervisor_resets_delay_after_ten_minutes_of_healthy_running(monkeypatch):
    import supervisor

    moment = [1000.0]
    monkeypatch.setattr(supervisor.time, "time", lambda: moment[0])
    restart = AutoRestart()
    restart.delay = 960
    assert not restart.tick(True, BotState.RUNNING, True)
    moment[0] += RESTART_STABLE_SECONDS - 1
    assert not restart.tick(True, BotState.RUNNING, True)
    assert restart.delay == 960
    moment[0] += 1
    assert not restart.tick(True, BotState.RUNNING, True)
    assert restart.delay == RESTART_DELAY_MIN
    # The controller honors manual shutdown; it won't restart a stopped bot.
    assert not restart.tick(False, BotState.IDLE, True)
    assert restart.restart_at is None
