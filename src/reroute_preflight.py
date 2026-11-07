"""Read-only reroute preflight using the aircraft's live detail page.

A route may be created only after the old route is explicitly grounded.
The current automation cannot safely complete the transaction without
verified game's Ground/Restore controls, so this module NEVER submits one.
It provides a narrow, privacy-preserving diagnostic for development.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from route_registry import endpoint, same_route

log = logging.getLogger("am4bot.rutas")
_GAME_ID = re.compile(r"^[0-9]{1,14}$")

# fleet_details.php contains the verified route-level ground link. Do not
# confuse the route ID with the aircraft ID.
_DETAILS_JS = """
const area = document.getElementById("detailsAction");
if (!area) return null;
const html = area.innerHTML || "";
const actions = Array.from(area.querySelectorAll("[onclick],[href]"))
  .map(el => (el.getAttribute("onclick") || el.getAttribute("href") || ""))
  .filter(v => /fleet_ground\\.php\\?id=\\d+/.test(v));
const groundIds = Array.from(new Set([
  ...actions.map(v => (v.match(/fleet_ground\\.php\\?id=(\\d+)/) || [])[1]),
  ...(html.match(/fleet_ground\\.php\\?id=\\d+/g) || []).map(v => v.match(/id=(\\d+)/)[1])
].filter(Boolean)));
const airports = Array.from(area.querySelectorAll(".col-5.bg-light span.l-text.exo"))
  .map(el => (el.textContent || "").trim().toUpperCase())
  .filter(v => /^[A-Z]{3,4}$/.test(v));
const arriveLabel = /(?:arrives|chega)\\s+in?\\s*<span[^>]*id=['"]timer['"]/i.test(html);
const timer = html.match(/timer\\(\\s*['"]timer['"]\\s*,\\s*(\\d+)\\s*\\)/);
return {
  ground_route_ids: groundIds,
  endpoints: airports.length === 2 ? airports : [],
  in_flight: !!(arriveLabel && timer && Number(timer[1]) > 0),
  ground_controls: actions.length,
  has_details: html.length > 100
};
"""


@dataclass(frozen=True)
class ReroutePreflight:
    aircraft_id: str
    route_id: str = ""
    route_confirmed: bool = False
    reason: str = "nao_verificado"
    game_endpoints: tuple[str, ...] = ()


def check_existing_route(bot, aircraft_id: str, record: dict) -> ReroutePreflight:
    """Load game details only (mode=res); never ground, buy or change a route."""
    aircraft_id = str(aircraft_id or "")
    if not _GAME_ID.fullmatch(aircraft_id):
        return ReroutePreflight(aircraft_id, reason="id_aeronave_invalido")
    try:
        bot.ajax(f"fleet_details.php?id={aircraft_id}", "detailsAction")
        info = bot.js(_DETAILS_JS) or {}
    except Exception as exc:  # read-only review cannot stop a full operating cycle
        log.warning("Pré-validação de rota %s indisponível: %s.",
                    aircraft_id, type(exc).__name__)
        return ReroutePreflight(aircraft_id, reason="detalhes_do_jogo_indisponiveis")
    if not info.get("has_details"):
        return ReroutePreflight(aircraft_id, reason="painel_da_aeronave_vazio")
    ids = list(dict.fromkeys(str(v) for v in (info.get("ground_route_ids") or []) if _GAME_ID.fullmatch(str(v))))
    if len(ids) != 1:
        return ReroutePreflight(aircraft_id, reason="id_da_rota_ambigua_ou_ausente")
    if info.get("in_flight"):
        return ReroutePreflight(aircraft_id, route_id=ids[0], reason="aeronave_ainda_em_voo")
    codes = tuple(str(v).strip().upper() for v in (info.get("endpoints") or []))
    if len(codes) != 2:
        return ReroutePreflight(aircraft_id, route_id=ids[0], reason="aeroportos_nao_exibidos_nos_detalhes")
    seen = {"origin": endpoint(code=codes[0]), "destination": endpoint(code=codes[1])}
    if not same_route(record, seen):
        return ReroutePreflight(aircraft_id, route_id=ids[0],
                                reason="rota_divergente_dos_detalhes", game_endpoints=codes)
    return ReroutePreflight(aircraft_id, route_id=ids[0],
                            route_confirmed=True, reason="rota_confirmada",
                            game_endpoints=codes)
