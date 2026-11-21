"""Leitura conservadora dos hubs adquiridos, isolada por perfil.

O seletor de pesquisa do jogo confirma apenas a lista de bases. Ele NÃO
comprova a base de uma aeronave nem o lucro atribuível àquela base.
Nenhum método deste módulo envia comandos ao jogo.
"""
from __future__ import annotations

import json
import math
import re
import threading
import time
from pathlib import Path
from typing import Optional

import paths
from airport_catalog import game_code

_LOCK = threading.RLock()
_AIRPORT_ID = re.compile(r"^[0-9]{1,12}$")
_CODE = re.compile(r"^[A-Z]{3,4}$")
_HUB_AGE_LIMIT = 24 * 60 * 60
_ESTIMATE_AGE_LIMIT = 7 * 24 * 60 * 60


def inventory_file() -> Path:
    return paths.current().data / "hub_inventory.json"


def _load(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return result if isinstance(result, dict) else {}


def _valid_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class HubInventory:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else inventory_file()

    def record_options(self, options: object, *, at: Optional[int] = None) -> bool:
        """Persist the full verified research hub selector; ignore placeholders.

        Failure never replaces the previously valid reading. Partial, malformed
        or conflicting selectors must not erase real hubs from the local cache.
        """
        if not isinstance(options, list) or not 0 < len(options) <= 500:
            return False
        hubs = []
        seen = set()
        for option in options:
            if not isinstance(option, dict):
                return False
            ident = str(option.get("id") or "").strip()
            if not ident or ident == "0":
                continue  # Game's "choose a base" placeholder.
            if not _AIRPORT_ID.fullmatch(ident) or ident in seen:
                return False
            seen.add(ident)
            raw_code = str(option.get("code") or "").strip().upper()
            code = raw_code if _CODE.fullmatch(raw_code) else game_code(ident)
            name = str(option.get("text") or option.get("title") or "").strip()[:120]
            if not name:
                return False
            hubs.append({"id": ident, "name": name, "code": code})
        if not hubs:
            return False  # Empty selector is not evidence of zero purchased hubs.
        stamp = int(time.time() if at is None else at)
        if stamp <= 0:
            return False
        data = {"version": 1, "source": "game_research_hub_select",
                "read_at": stamp, "hubs": hubs}
        try:
            with _LOCK:
                paths.write_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=2))
        except OSError:
            return False  # Never break the automation because a read-only cache is unwritable.
        return True

    def snapshot(self, route_report: Optional[dict] = None, *, now: Optional[int] = None) -> dict:
        """Compose an honest read-only report from *verified* home-base evidence.

        A route's departure/arrival airports and the maintenance at_base flag
        cannot prove which hub owns a plane. Until a producer records
        home_base_id + home_base_source='game', aircraft remain unassigned.
        """
        with _LOCK:
            raw = _load(self.path)
        current = int(time.time() if now is None else now)
        read_at = raw.get("read_at")
        read_at = read_at if _valid_number(read_at) and 0 < read_at <= current else None
        hubs = []
        for item in raw.get("hubs", []) if isinstance(raw.get("hubs"), list) and read_at else []:
            if (not isinstance(item, dict) or
                    not _AIRPORT_ID.fullmatch(str(item.get("id") or ""))):
                continue
            hubs.append({
                "id": str(item["id"]),
                "name": str(item.get("name") or "")[:120],
                "code": str(item.get("code") or "")[:4],
                "confirmed_aircraft": 0,
                "aircraft": [],
                "profit_per_day": None,
                "profit_coverage": 0,
            })
        by_id = {item["id"]: item for item in hubs}
        report = route_report if isinstance(route_report, dict) else {}
        relations = report.get("relations") if isinstance(report.get("relations"), list) else []
        unconfirmed = []
        unique = set()
        for row in relations:
            if not isinstance(row, dict):
                continue
            aircraft_id = str(row.get("aircraft_id") or "")
            if not aircraft_id or aircraft_id in unique:
                continue
            unique.add(aircraft_id)
            base_id = str(row.get("home_base_id") or "")
            source = row.get("home_base_source")
            stamp = row.get("home_base_verified_at")
            proven = (source == "game" and _valid_number(stamp) and
                      0 < stamp <= current and base_id in by_id)
            if not proven:
                unconfirmed.append({
                    "aircraft_id": aircraft_id,
                    "registration": str(row.get("registration") or aircraft_id)[:80],
                    "model": str(row.get("model") or "")[:100],
                })
                continue
            hub = by_id[base_id]
            hub["confirmed_aircraft"] += 1
            hub["aircraft"].append({
                "aircraft_id": aircraft_id,
                "registration": str(row.get("registration") or aircraft_id)[:80],
                "model": str(row.get("model") or "")[:100],
                "route": str(row.get("route_key") or "")[:120],
                "status": str(row.get("status") or "")[:80],
            })
            profit = row.get("profit_per_day")
            calc_at = row.get("profit_calculated_at")
            if (row.get("route_key") and row.get("profit_route_key") == row["route_key"]
                    and _valid_number(profit) and _valid_number(calc_at)
                    and 0 < calc_at <= current and current - calc_at <= _ESTIMATE_AGE_LIMIT):
                hub["profit_per_day"] = round((hub["profit_per_day"] or 0) + profit, 2)
                hub["profit_coverage"] += 1
        return {
            "source": raw.get("source") if hubs else None,
            "read_at": read_at if hubs else None,
            "stale": not hubs or current - read_at > _HUB_AGE_LIMIT,
            "hubs": hubs,
            "total_hubs": len(hubs),
            "observed_aircraft": len(unique),
            "unconfirmed_aircraft": unconfirmed,
            "partial": True,  # Registries may contain only visited fleet pages.
            "message": ("Bases ainda não verificadas no jogo." if not hubs else
                        "Inventário baseado na última leitura do seletor do jogo."),
        }
