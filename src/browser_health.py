"""ChromeDriver transport-failure diagnostics without reading account secrets.

A refused connection to Selenium's localhost port means the bot cannot
reach the driver process. It does NOT, by itself, prove an out-of-memory
kill; process status and the host's kernel journal are needed for that.
"""
from __future__ import annotations

import os
from pathlib import Path


_TRANSPORT_MARKERS = (
    "httpconnectionpool(host='localhost'",
    'httpconnectionpool(host="localhost"',
    "newconnectionerror",
    "connection refused",
    "failed to establish a new connection",
    "max retries exceeded with url: /session/",
    "invalid session id",
    "chrome not reachable",
    "disconnected: not connected to devtools",
)


def is_driver_disconnected(exc: Exception) -> bool:
    """Distinguish dead local Selenium transport from ordinary page timeouts."""
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSPORT_MARKERS)


def user_facing_error(exc: Exception) -> str:
    """Never forward verbose local session/element URLs to Telegram."""
    if is_driver_disconnected(exc):
        return (
            "ChromeDriver desconectou do bot (conexão local recusada ou "
            "sessão do Chrome encerrada). Reinício controlado programado."
        )
    return (str(exc).splitlines() or [type(exc).__name__])[0][:250]


def _mem_available_mib() -> str:
    try:
        with Path("/proc/meminfo").open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return f"{int(line.split()[1]) // 1024} MiB"
    except (OSError, ValueError, IndexError):
        pass
    return "desconhecida"


def driver_health_details(driver: object) -> str:
    """Log only the driver's own process state and total free host memory."""
    service = getattr(driver, "service", None)
    process = getattr(service, "process", None)
    pid = getattr(process, "pid", None)
    state = "indisponível"
    if process is not None:
        try:
            code = process.poll()
            state = "rodando" if code is None else f"encerrado (código {code})"
        except (OSError, AttributeError):
            state = "não consultável"
    return (
        f"PID ChromeDriver={pid if isinstance(pid, int) else '?'}; "
        f"processo={state}; RAM disponível do host={_mem_available_mib()}; "
        "causa do encerramento ainda não confirmada. "
        "Verifique data/logs/chromedriver.log e "
        "journalctl -k --since '30 minutes ago' (OOM/kill/segfault)."
    )
