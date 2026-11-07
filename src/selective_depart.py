"""Safe individual-flight dispatch using only controls supplied by the live game.

No mode=all&ids=x requests or guessed endpoints are sent. When the game only
offers the native bulk control, the dispatcher reports the limitation and
leaves the fleet alone rather than inadvertently launching blocked aircraft.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from urllib.parse import parse_qs

from route_registry import RouteRegistry

log = logging.getLogger("am4bot.vuelos")
_ID = re.compile(r"^[0-9]{1,14}$")
_REQUEST = re.compile(r"route_depart\.php\?([A-Za-z0-9_.=%&,+-]{1,220})", re.I)

# The game status tab uses #landedList/#flightStatus<aircraft-id>.
# Only a *native row-scoped action* is eligible for individual submission.
_LANDED_JS = """
return Array.from(document.querySelectorAll("#landedList [id^='flightStatus']")).map(row => {
  const hit = row.id.match(/^flightStatus(\\d+)$/);
  const links = Array.from(row.querySelectorAll("[onclick],[href]"))
    .filter(el => /route_depart\\.php\\?/i.test(
      (el.getAttribute("onclick") || "") + " " + (el.getAttribute("href") || "")))
    .map(el => ({
      value: el.getAttribute("onclick") || el.getAttribute("href") || "",
      tag: el.tagName
    }));
  return {id: hit ? hit[1] : "", native_actions: links};
}).filter(row => row.id !== "");
"""

_MARK_ACTION_JS = """
const id = String(arguments[0]), expected = String(arguments[1]);
if (!/^\\d{1,14}$/.test(id)) return false;
const container = document.getElementById("landedList");
const row = document.getElementById("flightStatus" + id);
if (!container || !row || !container.contains(row)) return false;
const matches = Array.from(row.querySelectorAll("[onclick],[href]")).filter(el => {
  const value = el.getAttribute("onclick") || el.getAttribute("href") || "";
  return /route_depart\\.php\\?/i.test(value);
});
if (matches.length !== 1) return false;
const action = matches[0];
const current = action.getAttribute("onclick") || action.getAttribute("href") || "";
if (current !== expected || action.disabled || action.getAttribute("aria-disabled") === "true") return false;
container.querySelectorAll("[data-am4-safe-depart]").forEach(el =>
  el.removeAttribute("data-am4-safe-depart"));
action.setAttribute("data-am4-safe-depart", id);
return true;
"""

_VERIFY_DEPARTED_JS = """
const id = String(arguments[0]);
const inflight = document.getElementById("inflightList");
const item = document.getElementById("flightStatus" + id);
return !!item && !!inflight && inflight.contains(item);
"""


@dataclass(frozen=True)
class DispatchDecision:
    aircraft_id: str
    approved: bool
    reason: str
    registration: str = ""


def _rank_for_keep(row: dict) -> tuple:
    profit = row.get("profit_per_day")
    return (
        -(profit if isinstance(profit, (int, float)) else -1),
        row.get("assigned_at", 0), str(row.get("aircraft_id", "")),
    )


def plan_dispatch(landed_ids: list[str], report: dict, *, now: float | None = None,
                  max_age_seconds: int = 180) -> list[DispatchDecision]:
    """Authorize only freshly read routes; hold one aircraft per duplicate pair.

    The registry may accumulate historical routes from pages not currently
    visible; landing status is independently checked against the game's live
    #landedList in the current cycle. Unknown aircraft remain blocked.
    """
    now = time.time() if now is None else now
    rows = {str(r.get("aircraft_id")): r for r in report.get("relations", [])}
    blocked: set[str] = set()
    for group in report.get("duplicates", []):
        group_rows = [rows[str(a.get("id"))] for a in group.get("aircraft", [])
                      if str(a.get("id")) in rows]
        if len(group_rows) > 1:
            group_rows.sort(key=_rank_for_keep)
            blocked.update(str(row["aircraft_id"]) for row in group_rows[1:])
    decisions = []
    for aircraft_id in dict.fromkeys(str(value) for value in landed_ids):
        if not _ID.fullmatch(aircraft_id):
            continue
        row = rows.get(aircraft_id)
        registration = str(row.get("registration") or aircraft_id) if row else aircraft_id
        if row is None or not row.get("origin") or not row.get("destination"):
            reason = "rota_nao_identificada"
        elif row.get("source") != "game":
            reason = "rota_nao_confirmada_no_jogo"
        elif not row.get("route_key"):
            reason = "sem_rota"
        elif not isinstance(row.get("game_verified_at"), (int, float)) or (
            now - row["game_verified_at"] < 0 or
            now - row["game_verified_at"] >= max_age_seconds
        ):
            reason = "leitura_de_rota_expirada"
        elif aircraft_id in blocked:
            reason = "rota_duplicada_reservada"
        else:
            reason = "aprovada"
        decisions.append(DispatchDecision(aircraft_id, reason == "aprovada",
                                          reason, registration))
    return decisions


def verified_native_action(aircraft_id: str, actions: list[dict]) -> str:
    """Recognize an exact per-plane departure action from the game's own DOM.

    The global mode=all&ids=x action is NEVER eligible. Only a *literal*
    numeric id/ids parameter matching this row is accepted.
    """
    if not _ID.fullmatch(str(aircraft_id)) or len(actions) != 1:
        return ""
    value = str(actions[0].get("value") or "")
    found = _REQUEST.search(value)
    if not found:
        return ""
    query = parse_qs(found.group(1), keep_blank_values=True)
    id_values = [v for key in ("id", "ids") for v in query.get(key, [])]
    if len(id_values) != 1 or id_values[0] != str(aircraft_id):
        return ""
    if query.get("ids") == ["x"] or any(not _ID.fullmatch(v) for v in id_values):
        return ""
    if "mode" not in query or not query["mode"][0]:
        return ""
    # Unknown server interpretation of mode=all: never send it, even if ids
    # contains only one aircraft. The endpoint might ignore ids entirely.
    if query["mode"][0].lower() == "all":
        return ""
    # Do not execute a URL copied from logs or stored history; only from a
    # per-aircraft control found in today's live landed row.
    return value


def collect_dispatch_rows(bot) -> list[dict]:
    return bot.js(_LANDED_JS) or []


def selective_dispatch(bot, registry: RouteRegistry, *, limit: int = 20) -> dict:
    """Execute verified per-aircraft native controls, never the Depart All button.

    Confirm each flight actually moved to the game's inflight list before
    counting it or attempting another. When the game doesn't expose a
    one-plane control, operate in read-only mode and record the blocker.
    """
    landed = collect_dispatch_rows(bot)
    report = registry.snapshot(allow_duplicates=False)
    decisions = plan_dispatch([row.get("id") for row in landed], report)
    native = {str(row["id"]): row.get("native_actions") or [] for row in landed}
    eligible = [d for d in decisions if d.approved]
    rejected = [d for d in decisions if not d.approved]
    exposed = [d for d in eligible if verified_native_action(
        d.aircraft_id, native.get(d.aircraft_id, []))]
    unexposed = len(eligible) - len(exposed)
    log.info(
        "Despacho individual: %d prontas na interface, %d aprovadas na política, "
        "%d bloqueadas por rota, %d com controle individual verificável, "
        "%d sem controle individual. Nunca usa Decolar todas com duplicidades.",
        len(decisions), len(eligible), len(rejected), len(exposed), unexposed,
    )
    for d in rejected[:10]:
        log.info("Despacho retido: %s (ID %s): %s.", d.registration, d.aircraft_id, d.reason)
    summary = {
        "at": int(time.time()), "ready_seen": len(decisions),
        "approved": len(eligible), "blocked": len(rejected),
        "native_individual": len(exposed), "not_supported": unexposed,
        "departed": 0, "status": "simulacao" if bot.dry_run else "pendente",
        "blocked_aircraft": [
            {"id": d.aircraft_id, "registration": d.registration, "reason": d.reason}
            for d in rejected[:40]
        ],
    }
    registry.record_dispatch_summary(summary)
    if bot.dry_run:
        log.info("[SIMULAÇÃO] Despacho individual: nenhuma ordem enviada.")
        return summary
    if not exposed:
        log.warning(
            "Despacho individual indisponível: a interface do jogo não expôs "
            "um comando específico para nenhuma aeronave aprovada. "
            "O botão geral permanece bloqueado para proteger as rotas duplicadas."
        )
        summary["status"] = "controle_individual_nao_disponivel"
        registry.record_dispatch_summary(summary)
        return summary
    for decision in exposed[:max(0, int(limit))]:
        if bot.stopping or bot.dry_run:
            break
        latest = {str(r.get("id")): r for r in collect_dispatch_rows(bot)}
        row = latest.get(decision.aircraft_id)
        if row is None:
            continue
        action = verified_native_action(decision.aircraft_id, row.get("native_actions") or [])
        if not action:
            log.warning("Despacho individual: comando mudou para %s. Abortando.", decision.registration)
            break
        # Fresh route evidence and duplicate decisions before each irreversible click.
        reevaluated = plan_dispatch([decision.aircraft_id], registry.snapshot(allow_duplicates=False))
        if len(reevaluated) != 1 or not reevaluated[0].approved:
            log.warning("Despacho individual: %s perdeu elegibilidade. Abortando.", decision.registration)
            break
        if not bot.js(_MARK_ACTION_JS, decision.aircraft_id, action):
            log.warning("Despacho individual: o jogo alterou o botão de %s. Abortando.", decision.registration)
            break
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import WebDriverException
        try:
            control = bot.driver.find_element(
                By.CSS_SELECTOR,
                f'#landedList [data-am4-safe-depart="{decision.aircraft_id}"]',
            )
            if bot.dry_run or bot.stopping:
                break
            # Selenium real click only. Don't fallback to an untrusted JS click.
            control.click()
        except WebDriverException as exc:
            log.warning("Despacho individual: clique não confirmado em %s (%s).",
                        decision.registration, exc.__class__.__name__)
            break
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException
        try:
            WebDriverWait(bot.driver, 8).until(
                lambda driver, aircraft_id=decision.aircraft_id: bool(driver.execute_script(_VERIFY_DEPARTED_JS, aircraft_id))
            )
        except TimeoutException:
            log.warning(
                "Despacho individual: decolagem de %s foi acionada, mas "
                "o jogo não confirmou o avião em voo. Interrompendo os demais.",
                decision.registration,
            )
            summary["status"] = "decolagem_sem_confirmacao"
            break
        summary["departed"] += 1
        summary["status"] = "decolagens_confirmadas"
        bot.count("departures")
        log.info("Despacho individual confirmado: %s (ID %s).",
                 decision.registration, decision.aircraft_id)
    registry.record_dispatch_summary(summary)
    return summary
