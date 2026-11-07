"""Experimental AM4 targeted departure with an explicit ID list.

Third-party AM4 clients use route_depart.php?mode=all&ids=<ids>, while the
game's own Depart All uses ids=x. The server-side distinction has NOT been
validated in this user's authenticated session. Therefore this path is OFF
by default and only one freshly approved plane is attempted per cycle after
the operator explicitly enables the experimental setting.

Never assume a successful HTTP response proves a departure. Compare the
game's real flight-status lists before and after and stop on surprises.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode

from route_registry import RouteRegistry

log = logging.getLogger("am4bot.vuelos")
_ID = re.compile(r"^[0-9]{1,14}$")

# Evidence that the current game page recognizes the original depart endpoint.
# Merely finding this control does NOT prove the backend respects an ids list.
_NATIVE_BULK_JS = """
return !!document.getElementById("runme") &&
 Array.from(document.querySelectorAll("[onclick]")).some(el =>
 /route_depart\\.php\\?mode=all&ids=x(?:[&'"]|$)/i.test(
   el.getAttribute("onclick") || ""
 ));
"""

_STATUS_JS = """
const read = id => {
  const el = document.getElementById(id);
  return el ? Array.from(el.querySelectorAll("[id^='flightStatus']"))
    .map(row => (row.id.match(/^flightStatus(\\d+)$/) || [])[1])
    .filter(Boolean) : [];
};
return {
  landed: read("landedList"),
  inflight: read("inflightList")
};
"""


def _valid_ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item) for item in items if _ID.fullmatch(str(item))}


def choose_target(approvals: list, current_landed: set[str], record: dict) -> str:
    """One and only one eligible ID; no extrapolation to unscanned aircraft."""
    from selective_depart import plan_dispatch

    fresh = plan_dispatch(
        [decision.aircraft_id for decision in approvals
         if decision.approved and decision.aircraft_id in current_landed],
        record,
    )
    for decision in fresh:
        if decision.approved and decision.aircraft_id in current_landed:
            return decision.aircraft_id
    return ""


def targeted_depart(bot, registry: RouteRegistry, approvals: list) -> dict:
    """Attempt ONE carefully checked ID; never use ids=x or batch unapproved IDs.

    Even with guardrails, this experimental action could dispatch more planes
    if the AM4 server ignores ids. It requires an explicit operator opt-in.
    """
    outcome = {"status": "experimental_indisponivel", "departed": 0, "target_id": ""}
    if not bot.config.get_bool("options", "experimental_id_batch_depart", False):
        outcome["status"] = "experimental_desativado"
        return outcome
    if bot.stopping:
        outcome["status"] = "bot_parando"
        return outcome
    if not bot.js(_NATIVE_BULK_JS):
        log.warning(
            "Despacho experimental: jogo não confirmou o endpoint nativo "
            "Depart All no DOM; nenhuma requisição enviada."
        )
        outcome["status"] = "contrato_do_jogo_nao_confirmado"
        return outcome
    before = bot.js(_STATUS_JS) or {}
    landed, inflight = _valid_ids(before.get("landed")), _valid_ids(before.get("inflight"))
    target = choose_target(approvals, landed, registry.snapshot(allow_duplicates=False))
    if not target or target in inflight:
        outcome["status"] = "nenhuma_aeronave_aprovada_agora"
        return outcome
    outcome["target_id"] = target
    if bot.dry_run:
        log.info(
            "[SIMULAÇÃO] Despacho experimental prepararia SOMENTE ID %s; "
            "nenhum pedido será enviado.",
            target,
        )
        outcome["status"] = "simulacao_lote_experimental"
        return outcome
    if bot.stopping or bot.dry_run:
        outcome["status"] = "bot_parando_ou_simulacao"
        return outcome
    if not registry.claim_experimental_departure(target):
        log.warning(
            "Despacho experimental: piloto único já utilizado anteriormente. "
            "Nenhum novo pedido por IDs será enviado automaticamente. "
            "Revisão manual necessária."
        )
        outcome["status"] = "piloto_experimental_ja_utilizado"
        return outcome
    # Two independent reference implementations send mode=all&ids=<numeric IDs>.
    # It is not proven that the game *honors* the filter, hence opt-in + 1/run.
    uri = "route_depart.php?" + urlencode({"mode": "all", "ids": target})
    log.warning(
        "Despacho experimental AUTORIZADO nas configurações: tentando apenas "
        "ID %s via lista explícita. A semântica deste endpoint NÃO foi "
        "validada no jogo autenticado. Não repetir automaticamente se incerto.",
        target,
    )
    outcome["status"] = "pedido_experimental_enviado_sem_confirmacao"
    try:
        bot.ajax(uri, "runme")
    except Exception as exc:
        log.error(
            "Despacho experimental: falha/timeout após possível envio de %s (%s); "
            "piloto bloqueado para outros ciclos.", target, type(exc).__name__,
        )
        outcome["status"] = "pedido_experimental_resultado_desconhecido"
        registry.finish_experimental_departure(target, outcome["status"])
        return outcome
    try:
        after = bot.js(_STATUS_JS) or {}
    except Exception as exc:
        log.error(
            "Despacho experimental: não foi possível verificar a resposta (%s). "
            "Piloto bloqueado até revisão manual.", type(exc).__name__,
        )
        outcome["status"] = "pedido_experimental_resultado_desconhecido"
        registry.finish_experimental_departure(target, outcome["status"])
        return outcome
    new_landed = _valid_ids(after.get("landed"))
    new_inflight = _valid_ids(after.get("inflight"))
    unexpected = (new_inflight - inflight) - {target}
    if unexpected:
        log.critical(
            "Despacho experimental: aeronaves NÃO aprovadas apareceram em voo "
            "(IDs %s). Desative esta opção e investigue o endpoint; não serão "
            "enviados novos pedidos neste ciclo.",
            ", ".join(sorted(unexpected)),
        )
        outcome["status"] = "alteracao_inesperada_no_jogo"
        registry.finish_experimental_departure(target, outcome["status"])
        return outcome
    if target in new_inflight and target not in new_landed:
        outcome["status"] = "decolagem_experimental_confirmada"
        outcome["departed"] = 1
        bot.count("departures")
        log.info("Despacho experimental: ID %s confirmado no painel de voos.", target)
    else:
        outcome["status"] = "pedido_experimental_sem_confirmacao"
        log.warning(
            "Despacho experimental: solicitação do ID %s não foi confirmada "
            "na lista de voos; piloto bloqueado para outros ciclos.",
            target,
        )
    registry.finish_experimental_departure(target, outcome["status"])
    return outcome
