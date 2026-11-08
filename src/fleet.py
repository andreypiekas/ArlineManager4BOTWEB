"""Fleet automation: routes for parked aircraft and buying the best-value aircraft.

Screen facts (verified 2026-09-30):
* Routes popup (`routes_main.php`): `#hParked` / `#hPending` counters;
  `fleet_parked.php` -> #routesContainer lists `#routeMainParkedList<id>` blocks.
* Research tab (`research_main.php` -> #routeAction): `#hubSelect` holds the hub id;
  `research_main.php?mode=search&rwy=..&dist=..&depId=..&arr=0&arrId=0&charter=0`
  -> #resResult with `.sorter` rows (data-distance / data-yclass / data-jclass /
  data-fclass / data-rwy, onclick contains `arr=<airportId>`).
* `route_research_route.php?dep=..&arr=..` -> #rDetails with `#capAc` (capable
  aircraft, option value "id;lat;lon;speed;range;arr") and "A/C on route".
* `new_route_info.php?id=<ac>&airportId=<arr>&mode=res` -> #newRouteInfo panel:
  `#introAuto` (autoprice), `#routeReg`, `#btnCreateNewRoute`, "Route fee".
* Order tab (`ac_orders.php?first=true` -> #routeAction): `#acListItems .acListItem`
  rows with data-range / data-speed / data-capacity / data-fuel / data-price and
  the model id in the onclick; `ac_orders.php?mode=detail&id=..&charter=0` ->
  #acModel with `#acReg`, `#hubSelection`, `#btnPurchaseIntro`, `#accountLow`.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from selenium.webdriver.common.by import By

from economy import (find_model, fmt_days, fmt_money, goal_progress, is_auto_goal, load_market, pick_ladder,
                     save_market)
from gamemode import EASY, GameMode
from helpers import clean_response, fmt, to_int
from notify import esc
from route_optimizer import rank_candidates
from route_strategy import best_reroute, profitable_candidates
from route_airports import match_hub_options, code_from_candidate, explain_hub_options
from airport_catalog import game_code
from route_registry import RouteRegistry, reroute_block_reason, endpoint, route_key
from reroute_preflight import check_existing_route

if TYPE_CHECKING:
    from bot import Bot

log = logging.getLogger("am4bot.rutas")
log_fleet = logging.getLogger("am4bot.flota")
log_market = logging.getLogger("am4bot.aviones")

MAX_ROUTE_TRIES = 16  # compare more profit-ranked destinations, including occupied-route fallbacks
BIG_SEATS = 150      # from this capacity an aircraft is "big": long routes, goal candidate
GOAL_SAFETY = 2      # a small aircraft must pay back in less than half the time left to the goal

# Everything below reads the game by structure (ids, classes, data attributes, onclick handlers),
# never by visible text, so the bot works with the game in English, Spanish or any other language.

# Route fee: the only bold red figure of the new-route panel.
_ROUTE_FEE_JS = """
const figures = document.querySelectorAll("#newRouteInfo .text-danger.font-weight-bold");
return figures.length ? figures[figures.length - 1].textContent : null;
"""
# "A/C on route": first row of the small table under the demand table in the route details.
_ON_ROUTE_JS = """
const cell = document.querySelector("#rDetails table.m-text:not(.table-bordered) tr td.text-right");
return cell ? cell.textContent : null;
"""

_PARKED_JS = """
return Array.from(document.querySelectorAll("#routesContainer [id^='routeMainParkedList']")).map(el => {
  const bolds = Array.from(el.querySelectorAll("b")).map(b => b.textContent.trim());
  const header = el.querySelector(".col-6.text-right");                 // "90 Seats" / "90 Asientos"
  const seats = ((header ? header.textContent : "").match(/[\\d,]+/) || [])[0];
  return {id: el.id.replace("routeMainParkedList", ""), model: bolds[0] || "?", reg: bolds[1] || "", seats: seats || ""};
});
"""

_CANDIDATES_JS = """
return Array.from(document.querySelectorAll("#resResult #list .sorter")).map(el => {
  const arr = ((el.getAttribute("onclick") || "").match(/arr=(\\d+)/) || [])[1];
  const title = el.querySelector(".exo");
  return {arr: arr || null, name: title ? title.textContent.trim() : "?",
          code: el.dataset.iata || el.dataset.icao || el.dataset.code || (title ? title.getAttribute("data-code") || title.title || "" : ""),
          distance: el.dataset.distance || "0",
          y: el.dataset.yclass || "0", j: el.dataset.jclass || "0", f: el.dataset.fclass || "0", rwy: el.dataset.rwy || "0"};
});
"""

_HUB_OPTIONS_JS = """
const select = document.getElementById("hubSelect");
return select ? Array.from(select.options).map(opt => ({
  id: opt.value, text: opt.textContent.trim(),
  code: opt.dataset.iata || opt.dataset.icao || opt.dataset.code || "",
  title: opt.title || ""
})) : [];
"""

_MODELS_JS = """
return Array.from(document.querySelectorAll("#acListItems .acListItem"))
  .filter(el => el.offsetParent !== null)
  .map(el => {
    const id = ((el.getAttribute("onclick") || "").match(/id=(\\d+)/) || [])[1];
    const name = el.querySelector("b");
    return {id: id || null, name: name ? name.textContent.trim() : "?", range: el.dataset.range || "0",
            speed: el.dataset.speed || "0", capacity: el.dataset.capacity || "0", fuel: el.dataset.fuel || "0",
            price: el.dataset.price || "0"};
  });
"""


@dataclass
class ParkedAircraft:
    id: str
    model: str
    reg: str
    seats: int


@dataclass
class RouteCandidate:
    arr_id: str
    name: str
    distance: float
    y: int
    j: int
    f: int
    runway: int
    code: str = ""  # game-confirmed IATA/ICAO when available


@dataclass
class AircraftModel:
    id: str
    name: str
    range_km: int
    speed: int
    capacity: int
    fuel: int
    price: int
    score: float = field(default=0.0)    # estimated net profit per day / price
    profit: float = field(default=0.0)   # estimated net profit per day ($)


# Economics calibrated on the airline's own flight history (01/10/2026, easy mode): the economy autoprice
# is 0.4 $/km + 170 and a leg takes distance / (1.5 x cruise speed) - both depend on the game mode, see
# gamemode.py -, the engine burns ~94 % of the listed fuel, CO2 is ~0.18 kg per passenger-km, and the bot
# leaves an aircraft ~6 minutes on the ground.
# The load factor is measured by the bot every cycle (it follows the airline reputation).
LOAD_DEFAULT = 0.55
TURNAROUND_H = 0.1
ENGINE_FUEL = 0.94
CO2_PER_PAX_KM = 0.18
ROUTE_DEMAND_Y = 1200   # economy passengers per day on a busy route: caps what one aircraft can sell


def daily_profit(model: AircraftModel, distance: int, load: float, fuel_price: float, co2_price: float,
                 mode: GameMode = EASY) -> float:
    """Estimated net profit per day of one aircraft flying *distance* km legs back to back
    (flight speed and economy autoprice of the game mode)."""
    if distance < 300 or model.price <= 0 or model.speed <= 0:
        return 0.0
    legs = 24 / (distance / (model.speed * mode.speed) + TURNAROUND_H)
    passengers = min(model.capacity * load * legs, ROUTE_DEMAND_Y)
    income = passengers * mode.fare(0, distance)
    fuel = legs * model.fuel * ENGINE_FUEL * distance * fuel_price / 1000
    co2 = passengers * CO2_PER_PAX_KM * distance * co2_price / 1000
    return income - fuel - co2


# ---------------------------------------------------------------------- entry point
# Only explicit DOM attributes or a dedicated route label count as game route
# evidence; never infer airports from general row text or the aircraft's model.
_ROUTE_AUDIT_JS = """
return Array.from(document.querySelectorAll("#popContent [id^='routeMainList']")).map(row => {
  // The existing seats module identifies routes by this real game link.
  const detailLink = row.querySelector("a[onclick*='fleet_details.php']");
  const link = detailLink || row.querySelector("a");
  const idFromLink = ((detailLink ? detailLink.getAttribute("onclick") : "") || "")
    .match(/fleet_details\\.php\\?id=(\\d+)/);
  const aircraftId = (idFromLink && idFromLink[1]) ||
    (row.id.match(/^routeMainList(\\d+)$/) || [])[1] || "";
  const label = link ? link.textContent.trim() : "";
  const tableData = Array.from(row.querySelectorAll("[data-dep], [data-arr], [data-origin], [data-destination], [data-route]"));
  const attrs = [row, ...tableData];
  const getAttr = (...names) => {
    for (const el of attrs) for (const name of names) {
      const value = el.getAttribute(name);
      if (value) return value.trim();
    }
    return "";
  };
  // Game-confirmed route label: .col-10 .s-text = "LEMD - EPRZ".
  // This selector already powers src/seats.py and works even without data-* attributes.
  const routeEl = row.querySelector(".col-10 .s-text") ||
    row.querySelector("[data-route], .route-name, .route-code, .routeName");
  const routeText = routeEl ? (routeEl.getAttribute("data-route") || routeEl.textContent || "").trim() : "";
  const codes = routeText.match(/\\b([A-Za-z]{3,4})\\s*(?:→|↔|–|—|-|\\/|to)\\s*([A-Za-z]{3,4})\\b/i);
  // An explicit hook containing BOTH dep and arr IDs is safe route evidence.
  const endpointHook = Array.from(row.querySelectorAll("[onclick], [href]"))
    .map(e => e.getAttribute("onclick") || e.getAttribute("href") || "")
    .find(v => /(?:[?&]|\\b)dep=\\d+/.test(v) && /(?:[?&]|\\b)arr=\\d+/.test(v)) || "";
  const depFromHook = (endpointHook.match(/(?:[?&]|\\b)dep=(\\d+)/) || [])[1] || "";
  const arrFromHook = (endpointHook.match(/(?:[?&]|\\b)arr=(\\d+)/) || [])[1] || "";
  const status = row.querySelector("[data-at-base], [data-at-hub], [data-grounded]");
  const atBaseRaw = status ? (status.getAttribute("data-at-base") ||
    status.getAttribute("data-at-hub") || status.getAttribute("data-grounded")) : "";
  return {
    aircraft_id: aircraftId,
    registration: label.split(" - ")[0] || aircraftId,
    model: label.includes(" - ") ? label.split(" - ").slice(1).join(" - ") : "",
    origin_id: getAttr("data-dep", "data-origin-id") || depFromHook,
    destination_id: getAttr("data-arr", "data-destination-id") || arrFromHook,
    origin_code: getAttr("data-origin-code", "data-dep-code") || (codes ? codes[1] : ""),
    destination_code: getAttr("data-destination-code", "data-arr-code") || (codes ? codes[2] : ""),
    route_label: routeText.slice(0, 80),
    at_base: atBaseRaw === "1" || atBaseRaw === "true" ? true :
      atBaseRaw === "0" || atBaseRaw === "false" ? false : null,
    in_flight: !!row.querySelector("[id^='routesTimer']")
  };
});
"""


def audit_routes(bot: "Bot", registry: RouteRegistry) -> None:
    """Accumulate verified relationships visible on the current page, never guess hidden pages."""
    rows = bot.js(_ROUTE_AUDIT_JS) or []
    # Maintenance was read earlier in this cycle. Unlike the routes list,
    # it exposes an explicit, per-aircraft at-base flag. Reuse it as read-only
    # ground evidence without revisiting paginated aircraft lists.
    recent = getattr(bot, "recent_fleet", None)
    fleet = recent(180) if callable(recent) else None
    grounded = {str(ac.id): ac.at_base for ac in fleet or []
                if getattr(ac, "id", None) is not None}
    maintenance_seen = 0
    maintenance_at_base = 0
    maintenance_away = 0
    detected = 0
    for row in rows:
        identity = str(row.get("aircraft_id") or "")
        if not identity:
            continue
        registration = row.get("registration") or identity
        model = row.get("model") or ""
        base = row.get("at_base")
        if identity in grounded:
            maintenance_seen += 1
            if grounded[identity] and not row.get("in_flight"):
                maintenance_at_base += 1
            else:
                maintenance_away += 1
        if row.get("in_flight"):
            base = False
        elif base is None and identity in grounded:
            base = grounded[identity]
        origin = endpoint(row.get("origin_id"), row.get("origin_code"))
        destination = endpoint(row.get("destination_id"), row.get("destination_code"))
        if registry.record(identity, registration, model, origin, destination, at_base=base):
            detected += 1
        else:
            registry.observe(identity, registration, model, at_base=base)
    missing = sum(1 for row in rows
                  if not ((row.get("origin_id") or row.get("origin_code"))
                          and (row.get("destination_id") or row.get("destination_code"))))
    registry.record_scan(len(rows), detected, missing)
    if rows:
        log.info(
            "Controle de rotas: %d aeronaves visíveis, %d rotas identificadas, "
            "%d sem os dois aeroportos no HTML da página. "
            "Modo simulação não impede a leitura.",
            len(rows), detected, missing,
        )
        if fleet is not None:
            log.info(
                "Controle de rotas: manutenção forneceu estado de %d aeronaves da página atual: "
                "%d na base, %d fora da base/em voo; demais sem comprovação.",
                maintenance_seen, maintenance_at_base, maintenance_away,
            )
    else:
        log.warning(
            "Controle de rotas: nenhuma aeronave reconhecida na página atual. "
            "Confirme que o jogo carregou a lista de rotas; não é necessário "
            "desativar o modo simulação para auditar."
        )


_ONBOARD_JS = """
return Array.from(document.querySelectorAll("#popContent [id^='routeMainList']"))
  .filter(row => row.querySelector("[id^='routesTimer']"))          // in flight: the row shows who is on board
  .map(row => {
    const link = row.querySelector("a");                              // "EC-003-2 - DC-9-10"
    const info = link ? link.parentElement.querySelector(".s-text") : null;   // "Onboard: 49 / 0 / 0" (Y / J / F)
    const nums = (((info || {}).textContent || "").match(/\\d+/g) || []).map(Number);
    // in economy slots: a business passenger takes 2, a first-class passenger 3
    return {name: link ? link.textContent.trim() : "", onboard: (nums[0] || 0) + 2 * (nums[1] || 0) + 3 * (nums[2] || 0)};
  });
"""


def measure_load(bot: "Bot") -> None:
    """Median load factor of the aircraft in flight (occupied economy slots / slots), smoothed over cycles."""
    market = load_market()
    loads = []
    for row in bot.js(_ONBOARD_JS) or []:
        model_name = row["name"].split(" - ", 1)[-1].strip()
        model = find_model(market, model_name)
        if model and model.get("capacity") and row["onboard"]:
            loads.append(min(1.0, row["onboard"] / model["capacity"]))
    if len(loads) >= 3:
        loads.sort()
        bot.record_load(loads[len(loads) // 2])


def manage_fleet(bot: "Bot") -> None:
    cfg = bot.config
    bot.open_popup("routes_main.php", "Routes", "nav_routes")
    measure_load(bot)
    parked = to_int(bot.js("return $('#hParked').text();")) or 0
    pending = to_int(bot.js("return $('#hPending').text();")) or 0
    bot.update_stats(parked=parked, pending=pending)
    log_fleet.info("%d aeronaves estacionadas sem rota, %d pendentes de entrega.", parked, pending)

    registry = RouteRegistry()
    audit_routes(bot, registry)
    budget = max(1, cfg.get_int("settings", "fleet_actions_per_cycle", 2))
    if not cfg.get_bool("options", "allow_duplicate_routes", True):
        repaired = resolve_duplicate_routes(bot, registry, budget)
        budget -= repaired
    if cfg.get_bool("options", "auto_route") and parked > 0 and budget > 0:
        created = create_routes(bot, budget)
        budget -= created
        parked -= created
    if cfg.get_bool("options", "autobuy_aircraft") and budget > 0:
        pending_duplicates = (not cfg.get_bool("options", "allow_duplicate_routes", False)
                              and registry.snapshot(allow_duplicates=False)["duplicate_routes"] > 0)
        if pending_duplicates:
            log_market.info("Compra de aeronave adiada: existem rotas duplicadas aguardando correção.")
        elif parked > 0:
            log_market.info("Não comprarei aeronaves enquanto houver %d estacionadas sem rota.", parked)
        else:
            buy_aircraft(bot)
    bot.close_popup()


# ---------------------------------------------------------------------- duplicate-route correction
def resolve_duplicate_routes(bot: "Bot", registry: RouteRegistry, budget: int) -> int:
    """Review persisted duplicate assignments and propose a more profitable route.

    Live reassignment of an already routed aircraft is intentionally disabled:
    the existing creation form cannot be assumed to replace a route. The game
    has a separate reroute UI, which must be verified before automation is safe.
    """
    report = registry.snapshot(allow_duplicates=False)
    if not report["duplicate_routes"]:
        return 0
    log.warning(
        "Controle de rotas: %d rotas duplicadas, %d aeronaves envolvidas.",
        report["duplicate_routes"], report["affected_aircraft"],
    )
    records = {row["aircraft_id"]: row for row in report["relations"]}
    for conflict in report["duplicates"]:
        names = ", ".join(
            f"{aircraft.get('registration') or aircraft.get('id')} (ID {aircraft.get('id')})"
            for aircraft in conflict["aircraft"]
        )
        log.warning(
            "Controle de rotas: duplicidade na rota %s | aeronaves: %s.",
            conflict.get("route") or "não identificada", names,
        )

    def pending(aircraft_id: str, reason: str, *, proposal: Optional[dict] = None) -> None:
        """Expose the precise blocker without altering the verified assignment."""
        item = records.get(str(aircraft_id), {})
        # When the analysis is paused or limited, retain the last profitable
        # proposal instead of erasing useful comparisons from the dashboard.
        if proposal is None and reason in (
            "pendente_limite_ciclo", "aguardando_ativacao_de_analise"
        ):
            proposal = item.get("proposal")
        registry.note(aircraft_id, reason, proposal=proposal)
        origin = item.get("origin") or {}
        destination = item.get("destination") or {}
        details = ""
        if reason == "aguardando_identificacao_da_rota":
            details = (
                f" (IDs dos aeroportos ausentes; códigos disponíveis: "
                f"{origin.get('code') or '?'} ↔ {destination.get('code') or '?'})"
            )
        elif reason == "aguardando_identificacao_da_base":
            details = " (o seletor de bases do jogo não confirmou um ID da rota)"
        elif reason == "rota_fora_das_bases":
            details = " (nenhuma ponta da rota é uma base selecionável; é necessário identificar a localização atual do avião e o controle de troca de rota)"

        elif reason == "sem_destino_com_codigo_validado":
            details = " (pesquisa não exibiu um código IATA/ICAO verificável para a alternativa)"
        elif reason == "aeronave_fora_da_base":
            details = " (o jogo indica que esta aeronave NÃO está numa base; a proposta permanece salva)"
        elif reason == "localizacao_nao_confirmada":
            details = " (o jogo não disponibilizou posição de base desta aeronave)"
        elif reason == "rota_nao_confirmada_no_jogo":
            details = " (rota registrada manualmente ou sem nova leitura do jogo)"
        elif reason == "aeroportos_nao_confirmados":
            details = " (IDs ou códigos de aeroportos insuficientes)"
        elif reason == "comprovacao_desatualizada":
            details = " (evidência da rota ou localização expirou; necessária nova leitura)"
        elif reason == "aguardando_confirmacao_no_jogo":
            details = " (necessário comprovar localização na base e rota atual)"
        elif reason == "troca_de_rota_ainda_nao_validada":
            details = " (formulário de criação de nova rota não comprova substituição da rota já atribuída)"
        elif reason == "sem_alternativa_melhor_que_atual":
            details = " (nenhuma alternativa lucrativa supera a estimativa da rota atual com a margem mínima)"
        elif reason == "aguardando_ativacao_de_analise":
            details = " (análise de rotas repetidas desligada; nenhuma pesquisa enviada ao jogo)"
        if proposal:
            details += (
                f" | alternativa: {proposal.get('destination') or proposal.get('destination_id')}"
                f", lucro estimado USD {fmt(proposal.get('profit_per_day', 0))}/dia"
            )
        log.info(
            "Controle de rotas: %s (ID %s), rota %s: %s%s. "
            "Nenhuma alteração enviada ao jogo.",
            item.get("registration") or aircraft_id, aircraft_id,
            item.get("route_key") or "?",
            reason.replace("_", " "), details,
        )

    # The planner does not change live routes; its own per-cycle budget must
    # be separate from the budget for creating/ordering aircraft.
    cfg = bot.config
    market = load_market()
    targets = []
    for duplicate in report["duplicates"]:
        members = [records[a["id"]] for a in duplicate["aircraft"] if a["id"] in records]
        if len(members) < 2:
            continue
        members.sort(key=lambda row: (
            -(row["profit_per_day"] if isinstance(row.get("profit_per_day"), (int, float)) else -1),
            row.get("assigned_at", 0), row["aircraft_id"],
        ))
        targets.extend(members[1:])
    # Fairness: previously unplanned targets first, then the oldest proposal.
    # Without this, the first N repeated routes were researched forever.
    targets.sort(key=lambda row: (
        row.get("last_planned_at") or 0,
        row["aircraft_id"],
    ))
    processed = 0
    if not cfg.get_bool("options", "analyze_duplicate_routes", True):
        for row in targets:
            pending(row["aircraft_id"], "aguardando_ativacao_de_analise")
        return 0
    for row in targets:
            aircraft_id = row["aircraft_id"]
            if processed >= budget or bot.stopping:
                pending(aircraft_id, "pendente_limite_ciclo")
                continue
            processed += 1
            registry.mark_plan_attempt(aircraft_id)
            origin = row.get("origin", {})
            destination = row.get("destination", {})
            hub_id = str(origin.get("id") or "")
            hub_code = origin.get("code") or ""
            current_dest_code = destination.get("code") or ""
            # The route list often exposes only IATA/ICAO codes, not numeric
            # airport IDs. Those codes are sufficient for a read-only lookup
            # against the game's real hub selection, not for guessing an ID.
            if not (hub_id and destination.get("id")) and not (hub_code and current_dest_code):
                pending(aircraft_id, "aguardando_identificacao_da_rota")
                continue
            model = find_model(market, row.get("model") or "")
            if not model or not model.get("speed") or not model.get("fuel"):
                pending(aircraft_id, "aguardando_dados_do_modelo")
                continue
            seats = int(model.get("capacity") or 0)
            if seats <= 0:
                pending(aircraft_id, "aguardando_dados_do_modelo")
                continue
            limit = cfg.get_int("settings", "route_max_distance_big" if seats >= BIG_SEATS else "route_max_distance", 6000)
            if model.get("range"):
                limit = min(limit, int(model["range"]))
            bot.open_popup("routes_main.php", "Routes", "nav_routes")
            bot.ajax("research_main.php", "routeAction")
            # Route labels are not direction-of-flight proof: for OSL↔DAC
            # either airport may be the actual hub. The unique match in the
            # authenticated game selector decides the planning origin.
            hub_options = bot.js(_HUB_OPTIONS_JS) or []
            hub_match = match_hub_options(
                hub_code, current_dest_code, hub_options
            ) if hub_code and current_dest_code else None
            if hub_match:
                hub_id = hub_match.airport_id
                hub_code = hub_match.code
                current_dest_code = hub_match.opposite_code
                log.info(
                    "Controle de rotas: %s — aeroporto %s (ID do jogo %s) consta das bases da "
                    "companhia; destino atual %s. Isso NÃO confirma a base desta aeronave.",
                    row["registration"], hub_code, hub_id, current_dest_code,
                )
            elif not (hub_id and destination.get("id")):
                diag = explain_hub_options(hub_code, current_dest_code, hub_options)
                log.warning(
                    "Controle de rotas: %s — seletor de bases: %s | opções %d "
                    "(IDs válidos %d, rótulos com possíveis códigos %d), "
                    "correspondências %s | exemplos: %s. "
                    "A rota pode estar entre aeroportos que não são bases próprias; "
                    "nenhuma base será presumida.",
                    row["registration"], diag["reason"], diag["total_options"],
                    diag["valid_ids"], diag["labels_with_possible_codes"],
                    diag["matched"], " / ".join(diag["samples"]) or "(nenhum)",
                )
                pending(
                    aircraft_id,
                    "rota_fora_das_bases" if diag["reason"] == "nenhuma_ponta_da_rota_nas_bases"
                    else "aguardando_identificacao_da_base",
                )
                continue
            # The game's hub picker must prove we are searching the same origin
            # as the existing assignment. Never optimize from an unrelated hub.
            selected = bot.js(
                "var e=document.getElementById('hubSelect');"
                "if(!e || !Array.from(e.options).some(x=>x.value===arguments[0]))return false;"
                "e.value=arguments[0];e.dispatchEvent(new Event('change',{bubbles:true}));"
                "return e.value===arguments[0];", hub_id,
            )
            if not selected:
                pending(aircraft_id, "aguardando_confirmacao_da_base")
                continue
            destination_options = []
            for distance in (limit, limit // 2, limit // 4):
                if distance < 500 or bot.stopping:
                    break
                options = []
                for candidate in search_routes(
                    bot, hub_id, distance, cfg.get_int("settings", "route_min_runway", 5000)
                ):
                    # Only a game-verifiable airport code allows comparison with
                    # the historical code-only records, in both directions.
                    if not candidate.code:
                        continue
                    if current_dest_code and candidate.code == current_dest_code:
                        continue
                    if destination.get("id") and destination["id"] == candidate.arr_id:
                        continue
                    if registry.is_occupied(
                        endpoint(code=hub_code), endpoint(code=candidate.code), aircraft_id
                    ):
                        continue
                    options.append(candidate)
                destination_options.extend(options)
                if options:
                    break
            if not destination_options:
                pending(aircraft_id, "sem_destino_com_codigo_validado")
                continue
            ranked = rank_candidates(
                destination_options, seats=seats, model=model, mode=bot.mode,
                load_factor=bot.load_factor(), fuel_price=bot.fuel_cost_basis(),
                co2_price=bot.co2_cost_basis(), premium=cfg.get_bool("options", "auto_seats"),
            )
            alternative, required_profit = best_reroute(
                ranked, current_profit=row.get("profit_per_day"),
                minimum_gain_percent=cfg.get_int("settings", "route_min_profit_gain_pct", 5),
            )
            if alternative is None:
                pending(
                    aircraft_id,
                    "sem_alternativa_melhor_que_atual" if required_profit is not None
                    else "sem_alternativa_lucrativa",
                )
                continue
            candidate, economics = alternative
            proposal = {
                "calculated_at": int(time.time()),
                "baseline_profit_per_day": (
                    round(float(row["profit_per_day"]))
                    if required_profit is not None else None
                ),
                "minimum_acceptable_profit_per_day": (
                    round(required_profit) if required_profit is not None else None
                ),
                "estimated_gain_per_day": (
                    round(economics.profit_per_day - float(row["profit_per_day"]))
                    if required_profit is not None else None
                ),
                "origin_id": hub_id, "origin_code": hub_code,
                "destination_id": candidate.arr_id, "destination_code": candidate.code,
                "destination": candidate.name, "distance_km": round(candidate.distance),
                "profit_per_day": round(economics.profit_per_day),
                "current_route": row.get("route_key", ""),
            }
            # Confirm the existing route's own live ID and endpoints from the
            # aircraft details before considering grounding/replacing it.
            # This is a read-only probe and never submits fleet_ground.php.
            preflight = check_existing_route(bot, aircraft_id, row)
            proposal["preflight"] = {
                "status": preflight.reason,
                "route_id": preflight.route_id,
                "endpoints": list(preflight.game_endpoints),
            }
            if preflight.route_confirmed:
                log.info(
                    "Controle de rotas: pré-validação de %s confirmou "
                    "rota interna ID %s e aeroportos %s.",
                    row["registration"], preflight.route_id,
                    " ↔ ".join(preflight.game_endpoints),
                )
            else:
                log.warning(
                    "Controle de rotas: pré-validação de %s pendente: %s. "
                    "Nenhuma rota será alterada.",
                    row["registration"], preflight.reason,
                )
            # The stored report identifies a collision, but a *fresh*, explicit
            # game reading must confirm the aircraft at base before changing it.
            reason = reroute_block_reason(row, verified_hub=hub_match is not None)
            if reason:
                pending(aircraft_id, reason, proposal=proposal)
                continue
            if not preflight.route_confirmed:
                pending(aircraft_id, "prevalidacao_de_rota_pendente", proposal=proposal)
                continue
            if bot.dry_run:
                pending(aircraft_id, "simulacao_redirecionamento", proposal=proposal)
                log.info("[SIMULAÇÃO] Redirecionaria %s para %s (lucro estimado ~ $%s/dia).",
                         row["registration"], candidate.name, fmt(proposal["profit_per_day"]))
                continue
            # Existing routed aircraft are NOT equivalent to parked aircraft
            # without routes. Our current create_route() uses a new-route form,
            # not the game's distinct "reroute" control. Until the existing
            # route replacement workflow is verified in a logged-in session,
            # only calculate and report proposals; never submit a new-route
            # purchase as a substitute for modifying an assigned aircraft.
            pending(aircraft_id, "troca_de_rota_ainda_nao_validada", proposal=proposal)
            continue

    log.info(
        "Controle de rotas: análise de %d/%d aeronaves com duplicidade neste ciclo; "
        "próximas serão priorizadas por proposta mais antiga.",
        processed, len(targets),
    )
    return 0  # Planning must never consume the live route-creation budget.


# ---------------------------------------------------------------------- routes
def read_parked(bot: "Bot") -> list[ParkedAircraft]:
    bot.ajax("fleet_parked.php", "routesContainer")
    parked = []
    registry = RouteRegistry()
    for row in bot.js(_PARKED_JS) or []:
        if row.get("id"):
            parked.append(ParkedAircraft(row["id"], row["model"], row["reg"] or row["id"], to_int(row["seats"]) or 0))
            registry.unassign(row["id"], row["reg"] or row["id"], row["model"])
    return parked


def search_routes(bot: "Bot", hub_id: str, max_distance: int, min_runway: int) -> list[RouteCandidate]:
    bot.ajax(
        f"research_main.php?mode=search&rwy={min_runway}&dist={max_distance}&depId={hub_id}&arr=0&arrId=0&charter=0",
        "resResult",
    )
    candidates = []
    for row in bot.js(_CANDIDATES_JS) or []:
        if not row.get("arr"):
            continue
        try:
            distance = float(row["distance"])
        except ValueError:
            distance = 0.0
        candidates.append(RouteCandidate(
            row["arr"], row["name"], distance,
            to_int(row["y"]) or 0, to_int(row["j"]) or 0, to_int(row["f"]) or 0, to_int(row["rwy"]) or 0,
            code_from_candidate(row),
        ))
    return candidates


def _daily_seats_sold(aircraft: ParkedAircraft, model: Optional[dict], distance: float, load: float,
                      mode: GameMode = EASY) -> float:
    """Economy passengers per day one aircraft would carry on a route of *distance* km (80 % of it, as margin)."""
    speed = (model or {}).get("speed") or 700
    legs = 24 / (max(distance, 300) / (speed * mode.speed) + TURNAROUND_H)
    return aircraft.seats * load * legs * 0.8


def _route_demand(candidate: RouteCandidate, premium: bool) -> int:
    """Daily demand in economy slots. With the seat layout by demand, business and first count too (2 and 3 slots)."""
    return candidate.y + 2 * candidate.j + 3 * candidate.f if premium else candidate.y


def create_routes(bot: "Bot", max_routes: int) -> int:
    cfg = bot.config
    parked = read_parked(bot)
    if not parked:
        log.info("Não há aeronaves estacionadas na lista da frota.")
        return 0
    max_distance = cfg.get_int("settings", "route_max_distance", 2000)
    max_distance_big = cfg.get_int("settings", "route_max_distance_big", 6000)
    min_runway = cfg.get_int("settings", "route_min_runway", 5000)
    market = load_market()
    premium = cfg.get_bool("options", "auto_seats")
    created = 0
    used_pairs: set[str] = set()
    registry = RouteRegistry()
    allow_duplicates = cfg.get_bool("options", "allow_duplicate_routes", True)

    for aircraft in parked:
        if created >= max_routes or bot.stopping:
            break
        # Big aircraft (150+ seats) earn most on long routes; never search beyond what the model can fly.
        limit = max_distance_big if aircraft.seats >= BIG_SEATS else max_distance
        known = find_model(market, aircraft.model)
        if known and known.get("range"):
            limit = min(limit, int(known["range"]))
        # Creating a route closes the popup, so start from a fresh Routes > Research screen every time.
        bot.open_popup("routes_main.php", "Routes", "nav_routes")
        bot.ajax("research_main.php", "routeAction")
        hub_id = bot.js("return $('#hubSelect').val() || (typeof depId !== 'undefined' ? String(depId) : null);")
        if not hub_id:
            log.warning("Não encontrei a base de origem na busca de rotas.")
            break
        outcome = "none"
        # If nothing suitable comes up (range, runway), retry with shorter searches.
        for distance in (limit, limit // 2, limit // 4):
            if distance < 500 or bot.stopping:
                break
            candidates = [
                c for c in search_routes(bot, hub_id, distance, min_runway)
                if c.arr_id != str(hub_id) and
                (allow_duplicates or (
                    route_key(endpoint(hub_id), endpoint(c.arr_id)) not in used_pairs
                    and not registry.is_occupied(
                        endpoint(hub_id), endpoint(c.arr_id), aircraft.id
                    )
                ))
            ]
            # Use the game's known demand and the latest cached aircraft model to
            # estimate daily revenue minus fuel/CO2; missing model data keeps the
            # original demand-based ordering (no fabricated fuel/speed values).
            ranked = rank_candidates(
                candidates, seats=aircraft.seats, model=known, mode=bot.mode,
                load_factor=bot.load_factor(),
                fuel_price=bot.fuel_cost_basis(), co2_price=bot.co2_cost_basis(),
                premium=premium,
            )
            estimates = {c.arr_id: estimate for c, estimate in ranked}
            profitable = profitable_candidates(ranked)
            has_estimates = any(estimate is not None for _, estimate in ranked)
            if has_estimates:
                tries = [candidate for candidate, _ in profitable[:MAX_ROUTE_TRIES]]
                if not tries:
                    log.warning(
                        "%s: rotas disponíveis até %d km apresentam lucro líquido "
                        "estimado não positivo; nenhuma taxa será paga por essas rotas.",
                        aircraft.reg, distance,
                    )
                    continue
                best = ranked[0][1]
                if best is not None:
                    log.info(
                        "%s: previsão de melhor rota: lucro ~ $%s/dia, receita ~ $%s/dia, "
                        "combustível ~ $%s/dia, CO₂ ~ $%s/dia (estimativas, não valores garantidos).",
                        aircraft.reg, fmt(int(best.profit_per_day)), fmt(int(best.revenue_per_day)),
                        fmt(int(best.fuel_cost_per_day)), fmt(int(best.co2_cost_per_day)),
                    )
            else:
                # No cached model yet: retain the known working demand heuristic.
                sorted_candidates = [candidate for candidate, _ in ranked]
                enough = [
                    c for c in sorted_candidates
                    if _route_demand(c, premium) >= _daily_seats_sold(
                        aircraft, known, c.distance, bot.load_factor(), bot.mode
                    )
                ]
                tries = (enough or sorted_candidates)[:MAX_ROUTE_TRIES]
            if not tries:
                log.info("Nenhuma rota candidata a até %d km (pista >= %d pés).", distance, min_runway)
                continue
            log.info("%s (%s, %d assentos): analisando as %d rotas com maior demanda até %d km ...",
                     aircraft.reg, aircraft.model, aircraft.seats, len(tries), distance)
            for candidate in tries:
                if bot.stopping:
                    break
                details = bot.ajax(f"route_research_route.php?dep={hub_id}&arr={candidate.arr_id}", "rDetails")
                capable = details.find_elements(By.XPATH, f".//*[@id='capAc']/option[starts-with(@value, '{aircraft.id};')]")
                if not capable:
                    log.debug("%s não pode voar para %s (alcance ou pista).", aircraft.reg, candidate.name)
                    continue
                on_route = to_int(bot.js(_ON_ROUTE_JS)) or 0
                if on_route and not allow_duplicates:
                    log.debug("%s já tem %d aeronaves.", candidate.name, on_route)
                    continue
                estimated = estimates.get(candidate.arr_id)
                outcome = create_route(
                    bot, aircraft, candidate, origin_id=hub_id,
                    profit_per_day=estimated.profit_per_day if estimated is not None else None,
                )
                break
            # An occupied route is not a valid outcome: continue with a shorter
            # search instead of giving up on this parked aircraft prematurely.
            if outcome != "none":
                break
        if outcome in ("created", "dry"):
            created += 1
            if not allow_duplicates:
                used_pairs.add(route_key(endpoint(hub_id), endpoint(candidate.arr_id)))
        elif outcome == "stop":
            break
        else:
            log.info("%s: nenhuma rota válida (alcance, pista ou rota já utilizada).", aircraft.reg)
    return created


def create_route(bot: "Bot", aircraft: ParkedAircraft, candidate: RouteCandidate,
                 *, origin_id: str = "", reroute: bool = False,
                 profit_per_day: Optional[float] = None) -> str:
    """Returns 'created', 'dry' (dry run) or 'stop' (money or page problem)."""
    bot.js("if (typeof hideFlightInfo === 'function') { hideFlightInfo(); } arrId = arguments[0];", int(candidate.arr_id))
    panel = bot.ajax(f"new_route_info.php?id={aircraft.id}&airportId={candidate.arr_id}&mode=res", "newRouteInfo")
    fee = to_int(bot.js(_ROUTE_FEE_JS))
    if not bot.can_spend(fee, f"a rota {candidate.name}", essential=not reroute):  # reroutes must preserve cash reserve
        bot.js("$('#newRouteInfo').hide();")
        return "stop"

    autoprice = panel.find_elements(By.XPATH, ".//*[@id='introAuto']")
    if autoprice:
        bot.click_element(autoprice[0])
        bot.pause(0.8, 1.2)
    prices = bot.js(
        "return ['eSeat', 'bSeat', 'fSeat'].map(i => { const e = document.getElementById(i); return e ? e.value : ''; });"
    ) or ["", "", ""]
    if not prices[0]:
        log.warning("O preço automático não preencheu as passagens de %s; a rota não será criada.", candidate.name)
        bot.js("$('#newRouteInfo').hide();")
        return "stop"
    reg = bot.js("return $('#routeReg').val();") or ""
    summary = (
        f"{candidate.name} ({candidate.distance:,.0f} km, demanda Y {candidate.y} / J {candidate.j} / F {candidate.f}) "
        f"para {aircraft.reg} ({aircraft.model}), passagens ${prices[0]} / ${prices[1]} / ${prices[2]}, "
        f"matrícula {reg}, taxa da rota ${fmt(fee)}"
    )
    if bot.dry_run:
        log.info("[SIMULAÇÃO] Criaria a rota %s.", summary)
        bot.notify(f"🧪 SIMULAÇÃO: criaria a rota {esc(summary)}.", silent=True, category="simulation")
        bot.js("$('#newRouteInfo').hide();")
        return "dry"

    before = bot.read_money()
    bot.click_element(panel.find_element(By.XPATH, ".//*[@id='btnCreateNewRoute']"))
    response = bot.wait_text("//*[@id='routeNewAction']", timeout=15)
    if not bot.confirm_purchase(before, fee, f"a rota {candidate.name}", "routeNewAction"):
        bot.js("$('#newRouteInfo').hide();")
        return "stop"
    bot.spent(fee, invest=True)
    bot.count("routes")
    if origin_id:
        RouteRegistry().record(
            aircraft.id, aircraft.reg, aircraft.model,
            endpoint(origin_id, code=game_code(origin_id), name=bot.js(
                "var e=document.getElementById('hubSelect');"
                "return e && e.selectedIndex>=0 ? e.options[e.selectedIndex].text : '';"
            ) or ""), endpoint(
                candidate.arr_id, code=game_code(candidate.arr_id, candidate.code),
                name=candidate.name,
            ),
            source="redirecionamento" if reroute else "criacao_confirmada",
            profit_per_day=profit_per_day,
            at_base=True,
        )
    log.info("%s: %s. %s", "Rota alterada" if reroute else "Rota criada", summary, clean_response(response))
    bot.notify(f"🛫 <b>Rota criada</b>: {esc(summary)}.\n{esc(clean_response(response, 200))}".rstrip(), category="routes")
    bot.js("$('#newRouteInfo').hide();")
    return "created"


# ---------------------------------------------------------------------- aircraft market
def read_models(bot: "Bot") -> list[AircraftModel]:
    models = []
    for row in bot.js(_MODELS_JS) or []:
        if not row.get("id"):
            continue
        models.append(AircraftModel(
            row["id"], row["name"], to_int(row["range"]) or 0, to_int(row["speed"]) or 0,
            to_int(row["capacity"]) or 0, to_int(row["fuel"]) or 0, to_int(row["price"]) or 0,
        ))
    return models


def score_models(bot: "Bot", models: list[AircraftModel]) -> None:
    """Estimate daily profit and return for every model, on the routes it will actually fly."""
    cfg = bot.config
    fuel_price = bot.fuel_cost_basis()
    co2_price = bot.co2_cost_basis()
    load = bot.load_factor()
    short = cfg.get_int("settings", "route_max_distance", 2000)
    long = cfg.get_int("settings", "route_max_distance_big", 6000)
    for model in models:
        distance = min(model.range_km, long if model.capacity >= BIG_SEATS else short)
        model.profit = daily_profit(model, distance, load, fuel_price, co2_price, bot.mode)
        model.score = model.profit / model.price if model.price > 0 else 0.0


def payback_days(model: AircraftModel) -> float:
    return 1 / model.score if model.score > 0 else float("inf")


def buy_aircraft(bot: "Bot") -> None:
    cfg = bot.config
    bot.open_popup("routes_main.php", "Routes", "nav_routes")
    bot.ajax("ac_orders.php?first=true", "routeAction")
    models = read_models(bot)
    if not models:  # the list sometimes renders a moment after the Ajax call returns
        bot.pause(1.5, 2.0)
        models = read_models(bot)
    if not models:
        log_market.warning("A lista do mercado de aeronaves está vazia.")
        return
    score_models(bot, models)
    save_market([{"id": m.id, "name": m.name, "price": m.price, "capacity": m.capacity, "range": m.range_km,
                  "speed": m.speed, "fuel": m.fuel, "score": round(m.score, 4), "profit": int(m.profit)}
                 for m in models])

    stats = bot.stats()
    if stats.money is None:
        log_market.warning("Saldo desconhecido; nenhuma aeronave será comprada.")
        return
    reserve = cfg.get_int("settings", "cash_reserve", 0)
    budget = stats.money - reserve
    max_price = cfg.get_int("settings", "aircraft_max_price", 0)
    hangar_free = stats.hangar_free

    goal_name = cfg.get("settings", "goal_model") if cfg.get_bool("options", "save_for_goal") else ""
    if goal_name:
        save_for_goal(bot, models, goal_name, budget, reserve, max_price, hangar_free)
        return

    if hangar_free is not None and hangar_free < 1:
        log_market.info("Hangar cheio: não há vaga para outra aeronave.")
        return
    preferred = cfg.get("settings", "aircraft_model")
    if preferred:
        wanted = [m for m in models if m.name.lower() == preferred.lower()] or \
                 [m for m in models if preferred.lower() in m.name.lower()]
        if not wanted:
            log_market.warning("Não encontrei o modelo '%s' no mercado.", preferred)
            return
        choice = wanted[0]
        if choice.price > budget:
            log_market.info("%s custa $%s, acima dos $%s disponíveis após a reserva de caixa.", choice.name, fmt(choice.price), fmt(budget))
            return
    else:
        affordable = [m for m in models if 0 < m.price <= budget and (max_price == 0 or m.price <= max_price) and m.score > 0]
        if not affordable:
            log_market.info("Nenhuma aeronave dentro dos $%s disponíveis após a reserva de caixa.", fmt(budget))
            return
        affordable.sort(key=lambda m: m.score, reverse=True)
        choice = affordable[0]
        log_market.info("Aeronaves mais rentáveis: %s", ", ".join(f"{m.name} ({m.score * 100:.0f}%/dia, ${fmt(m.price)})" for m in affordable[:3]))
    order_aircraft(bot, choice)


def save_for_goal(bot: "Bot", models: list[AircraftModel], goal_name: str, budget: int, reserve: int,
                  max_price: int, hangar_free: Optional[int]) -> None:
    """Savings mode: buy the goal aircraft as soon as it fits, and meanwhile only aircraft that
    pay for themselves well before the goal would be reached (they make the goal come sooner).
    With the automatic goal the target is the next step of the growth ladder."""
    stats = bot.stats()
    if is_auto_goal(goal_name):
        cfg = bot.config
        pick = pick_ladder([{"name": m.name, "price": m.price, "profit": m.profit} for m in models
                            if max_price == 0 or m.price <= max_price],
                           stats.income_day, cfg.get_int("settings", "ladder_budget_days", 1),
                           cfg.get_int("settings", "ladder_max_payback", 5), fallback_budget=max(budget, 0))
        goal = next((m for m in models if pick and m.name == pick["name"]), None)
        if goal is None:
            log_market.info("Progressão: nenhuma aeronave atende ao orçamento e ao prazo de retorno.")
            return
        log_market.info("Progressão: próxima aeronave %s (%s, %d assentos, rende ~%s/dia e se paga em ~%.1f dias).",
                        goal.name, fmt_money(goal.price), goal.capacity, fmt_money(int(goal.profit)), payback_days(goal))
    else:
        goal = next((m for m in models if m.name.lower() == goal_name.lower()), None) or \
            next((m for m in models if goal_name.lower() in m.name.lower()), None)
    if goal is None:
        log_market.warning("Não encontrei a aeronave desejada '%s' no mercado; nenhuma compra até corrigir a meta.", goal_name)
        return
    bot.update_stats(goal_price=goal.price)
    progress = goal_progress(goal.price, stats.money, reserve, stats.income_day)
    if progress is None:  # no price for the goal in the market list, or the balance is unknown
        log_market.info("Meta %s: sem preço ou saldo disponível; nenhuma compra neste ciclo.", goal.name)
        return
    status = (f"Objetivo {goal.name}: {fmt_money(progress['have'])} de {fmt_money(goal.price)} ({progress['pct']:.0f}%), "
              f"faltam {fmt_money(progress['missing'])}, previsão {fmt_days(progress['eta_days'])}")

    if progress["reached"]:
        if hangar_free is not None and hangar_free < 1:
            log_market.info("%s. Há saldo, mas não há vaga no hangar; será ampliado no próximo ciclo.", status)
            return
        log_market.info("🎯 Meta alcançada! %s", status)
        order_aircraft(bot, goal, goal=True)
        return

    if not bot.config.get_bool("options", "goal_invest"):
        log_market.info("%s. Apenas economizando.", status)
        return
    eta = progress["eta_days"]
    if eta is None:
        log_market.info("%s. Ainda não conheço o ritmo da receita; apenas economizando.", status)
        return
    if hangar_free is not None and hangar_free < 2:
        log_market.info("%s. Reservando a última vaga do hangar para a meta.", status)
        return
    candidates = [m for m in models
                  if m.name != goal.name and 0 < m.price <= budget and (max_price == 0 or m.price <= max_price)
                  and payback_days(m) * GOAL_SAFETY < eta]
    if not candidates:
        log_market.info("%s. Nenhuma outra aeronave acessível oferece retorno antes da meta; economizando.", status)
        return
    candidates.sort(key=lambda m: m.score, reverse=True)
    choice = candidates[0]
    log_market.info("%s. Comprando um %s porque se paga em ~%.1f dias e antecipa a meta.",
                    status, choice.name, payback_days(choice))
    order_aircraft(bot, choice)


def order_aircraft(bot: "Bot", choice: AircraftModel, goal: bool = False) -> bool:
    detail = bot.ajax(f"ac_orders.php?mode=detail&id={choice.id}&charter=0", "acModel")
    # O motor só pode ser escolhido antes de encomendar. Uma preferência
    # explícita NÃO aceita fallback silencioso para a seleção padrão do jogo.
    from engine_selection import EngineSelectionError, prepare_engine

    try:
        motor = prepare_engine(bot, bot.config.get("settings", "engine_preference", "default"))
    except EngineSelectionError as exc:
        log_market.warning("Compra de %s bloqueada: %s", choice.name, exc)
        return False
    if motor and not bot.dry_run:
        # A alteração de motor pode reconstruir todo o fragmento Ajax.
        detail = bot.driver.find_element(By.ID, "acModel")
    low = detail.find_elements(By.XPATH, ".//*[@id='accountLow']")
    if low and low[0].is_displayed():
        log_market.info("O jogo informa que não há saldo suficiente para um %s.", choice.name)
        return False
    reg = bot.js("return $('#acReg').val();") or ""
    summary = f"1 x {choice.name} por ${fmt(choice.price)} (matrícula {reg}, {choice.capacity} passageiros, {fmt(choice.range_km)} km de autonomia)"
    if motor:
        summary += f" | motor: {motor}"
    if bot.dry_run:
        log_market.info("[SIMULAÇÃO] Encomendaria %s.", summary)
        bot.notify(f"🧪 SIMULAÇÃO: encomendaria {esc(summary)}.", silent=True, category="simulation")
        return True
    before = bot.read_money()
    bot.click_element(detail.find_element(By.XPATH, ".//*[@id='btnPurchaseIntro']"))
    response = bot.wait_text("//*[@id='orderAction']", timeout=15)
    if not bot.confirm_purchase(before, choice.price, f"o pedido de {choice.name}", "orderAction"):
        return False
    bot.spent(choice.price, invest=True)
    bot.count("aircraft")
    free = bot.stats().hangar_free
    if free is not None:
        bot.update_stats(hangar_free=max(0, free - 1))
    log_market.info("Pedido: %s. %s", summary, clean_response(response))
    title = "🎯 <b>Meta alcançada! Aeronave encomendada</b>" if goal else "🛒 <b>Aeronave encomendada</b>"
    bot.notify(f"{title}: {esc(summary)}.\n{esc(clean_response(response, 200))}".rstrip(), category="aircraft")
    return True
