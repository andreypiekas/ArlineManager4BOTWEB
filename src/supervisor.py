"""Automatic restart after a crash (login failure, Chrome gone ...), shared by the desktop app and web mode."""
from __future__ import annotations

import logging
import time
from typing import Optional

from bot import BotState

log = logging.getLogger("am4bot.app")

RESTART_DELAY_MIN = 120    # seconds before the first automatic restart after an error
RESTART_DELAY_MAX = 1800   # the delay doubles on repeated failures up to this
RESTART_STABLE_SECONDS = 600  # ten healthy minutes before resetting backoff


class AutoRestart:
    def __init__(self) -> None:
        self.restart_at: Optional[float] = None
        self.delay = RESTART_DELAY_MIN
        self._running_since: Optional[float] = None

    @property
    def restart_in(self) -> Optional[int]:
        restart_at = self.restart_at  # read once: the web thread asks while tick() may clear it
        return max(0, int(restart_at - time.time())) if restart_at is not None else None

    def tick(self, alive: bool, state: BotState, enabled: bool) -> bool:
        """Call about once a second. Returns True when the bot should be started again now."""
        now = time.time()
        if alive:
            if state is BotState.RUNNING:
                if self._running_since is None:
                    self._running_since = now
                elif now - self._running_since >= RESTART_STABLE_SECONDS:
                    # Chrome must survive a meaningful interval. A brief
                    # transition to RUNNING no longer resets the penalty.
                    self.delay = RESTART_DELAY_MIN
            else:
                self._running_since = None
            self.restart_at = None
            return False
        self._running_since = None
        if state is not BotState.ERROR or not enabled:
            self.restart_at = None
            return False
        if self.restart_at is None:
            self.restart_at = now + self.delay
            log.warning("Reinício automático em %d min.", max(1, self.delay // 60))
        elif now >= self.restart_at:
            self.restart_at = None
            self.delay = min(self.delay * 2, RESTART_DELAY_MAX)
            log.info("Reiniciando o bot ...")
            return True
        return False
