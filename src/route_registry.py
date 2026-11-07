"""Persistent per-profile aircraft/route registry and undirected duplicate detection.

Only confirmed actions, explicit game attributes or deliberate manual corrections
can change a route assignment. A missing aircraft on a paginated game page does
not prove removal. The registry is a cache/audit trail, not game authority.
"""
from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Optional

import paths
from airport_catalog import same_airport_identity

_LOCK = threading.RLock()
_MAX_HISTORY = 1500
_AIRPORT_ID_RE = re.compile(r"^\d{1,12}$")
_IATA_RE = re.compile(r"^[A-Z]{3,4}$")


def registry_file() -> Path:
    return paths.current().data / "routes_registry.json"


def _normalize(raw: object) -> str:
    text = unicodedata.normalize("NFKD", str(raw or ""))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).strip().upper().split())


def endpoint(airport_id: object = "", code: object = "", name: object = "") -> dict:
    """Create a conservative endpoint identity, preferring game's stable airport ID."""
    ident = str(airport_id or "").strip()
    code_norm = _normalize(code)
    if not _AIRPORT_ID_RE.fullmatch(ident):
        ident = ""
    if not _IATA_RE.fullmatch(code_norm):
        code_norm = ""
    name_norm = _normalize(name)
    return {"id": ident, "code": code_norm, "name": str(name or "").strip(),
            "normalized_name": name_norm}


def endpoint_matches(a: dict, b: dict) -> bool:
    """Compare game IDs and verified IATA/ICAO aliases, never names when IDs conflict."""
    if a.get("id") and b.get("id"):
        return a["id"] == b["id"]
    if same_airport_identity(a, b):
        return True
    if (not a.get("id") and not b.get("id") and
            not a.get("code") and not b.get("code")):
        an, bn = a.get("normalized_name"), b.get("normalized_name")
        return bool(an and bn and an == bn)
    return False


def route_key(origin: dict, destination: dict) -> Optional[str]:
    """Canonical A↔B signature, independent of direction, only if both endpoints exist."""
    def code(value: dict) -> str:
        if value.get("id"):
            return "id:" + value["id"]
        if value.get("code"):
            return "code:" + value["code"]
        if value.get("normalized_name"):
            return "name:" + value["normalized_name"]
        return ""
    first, second = code(origin), code(destination)
    if not first or not second or first == second:
        return None
    return " ↔ ".join(sorted((first, second)))


def same_route(first: dict, second: dict) -> bool:
    a, b = first.get("origin", {}), first.get("destination", {})
    c, d = second.get("origin", {}), second.get("destination", {})
    return bool((endpoint_matches(a, c) and endpoint_matches(b, d)) or
                (endpoint_matches(a, d) and endpoint_matches(b, c)))


def reroute_block_reason(row: dict, now: Optional[float] = None,
                         *, verified_hub: bool = False) -> Optional[str]:
    """Return the exact reason a duplicate cannot be moved safely.

    The maintenance `at_base` flag means 'at a company base' and does not
    identify WHICH base; verified_hub merely establishes that an airport of
    the existing route appears in the player's hub selector. Neither is a
    proven, per-aircraft origin for a new routing action.
    """
    now = time.time() if now is None else now
    if row.get("source") != "game":
        return "rota_nao_confirmada_no_jogo"
    if row.get("at_base") is False:
        return "aeronave_fora_da_base"
    if row.get("at_base") is not True:
        return "localizacao_nao_confirmada"
    origin, destination = row.get("origin") or {}, row.get("destination") or {}
    both_ids = bool(origin.get("id") and destination.get("id"))
    verified_code_pair = bool(
        verified_hub and origin.get("code") and destination.get("code")
    )
    if not (both_ids or verified_code_pair):
        return "aeroportos_nao_confirmados"
    for stamp in ("game_verified_at", "grounded_confirmed_at"):
        recorded = row.get(stamp)
        if not isinstance(recorded, (int, float)):
            return "comprovacao_desatualizada"
        elapsed = now - recorded
        if elapsed < 0 or elapsed >= 180:
            return "comprovacao_desatualizada"
    return None


def eligible_for_reroute(row: dict, now: Optional[float] = None,
                         *, verified_hub: bool = False) -> bool:
    """Compatibility check for read-only planning. Not proof of safe live rerouting."""
    return reroute_block_reason(row, now, verified_hub=verified_hub) is None

def _state(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": 1, "aircraft": {}, "history": []}
    if not isinstance(data, dict) or not isinstance(data.get("aircraft", {}), dict):
        return {"version": 1, "aircraft": {}, "history": []}
    data.setdefault("history", [])
    return data


class RouteRegistry:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else registry_file()

    def _save(self, data: dict) -> None:
        paths.write_atomic(self.path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))

    def record(self, aircraft_id: str, registration: str, model: str,
               origin: dict, destination: dict, *, source: str = "game",
               profit_per_day: Optional[float] = None, at_base: Optional[bool] = None) -> bool:
        """Record a verified route; never overwrite another aircraft's identity."""
        aircraft_id = str(aircraft_id or "").strip()
        if not aircraft_id or route_key(origin, destination) is None:
            return False
        with _LOCK:
            data = _state(self.path)
            previous = data["aircraft"].get(aircraft_id, {})
            entry = dict(previous)
            entry.update({
                "aircraft_id": aircraft_id,
                "registration": str(registration or previous.get("registration") or aircraft_id),
                "model": str(model or previous.get("model") or "?"),
                "origin": origin,
                "destination": destination,
                "route_key": route_key(origin, destination),
                "source": source,
                "status": "ativa" if previous.get("route_key") != route_key(origin, destination) else previous.get("status", "ativa"),
                "last_seen": int(time.time()),
            })
            if profit_per_day is not None:
                entry["profit_per_day"] = round(float(profit_per_day), 2)
            if at_base is not None:
                entry["at_base"] = bool(at_base)
                if at_base and source == "game":
                    entry["grounded_confirmed_at"] = int(time.time())
                elif not at_base:
                    entry.pop("grounded_confirmed_at", None)
            if source == "game":
                entry["game_verified_at"] = int(time.time())
            if not previous or previous.get("route_key") != entry["route_key"]:
                entry["assigned_at"] = int(time.time())
                entry.pop("proposal", None)
                data["history"].append({
                    "at": int(time.time()), "aircraft_id": aircraft_id,
                    "registration": entry["registration"], "action": "rota_registrada" if not previous else "rota_alterada",
                    "previous": previous.get("route_key"), "route": entry["route_key"], "source": source,
                })
                data["history"] = data["history"][-_MAX_HISTORY:]
            data["aircraft"][aircraft_id] = entry
            self._save(data)
            return True

    def observe(self, aircraft_id: str, registration: str = "", model: str = "",
                at_base: Optional[bool] = None) -> bool:
        """Register an aircraft seen on the current routes page even if no route can be verified."""
        aircraft_id = str(aircraft_id or "").strip()
        if not aircraft_id:
            return False
        with _LOCK:
            data = _state(self.path)
            previous = data["aircraft"].get(aircraft_id, {})
            entry = dict(previous)
            entry.update({
                "aircraft_id": aircraft_id,
                "registration": str(registration or previous.get("registration") or aircraft_id),
                "model": str(model or previous.get("model") or "?"),
                "last_seen": int(time.time()),
            })
            if not previous:
                entry["status"] = "rota_nao_identificada"
            if at_base is not None:
                entry["at_base"] = bool(at_base)
                if at_base:
                    entry["grounded_confirmed_at"] = int(time.time())
                else:
                    entry.pop("grounded_confirmed_at", None)
            data["aircraft"][aircraft_id] = entry
            self._save(data)
            return True

    def unassign(self, aircraft_id: str, registration: str = "", model: str = "") -> bool:
        """A verified entry in the game's 'without route' list clears stale assignment."""
        aircraft_id = str(aircraft_id or "").strip()
        if not aircraft_id:
            return False
        with _LOCK:
            data = _state(self.path)
            previous = data["aircraft"].get(aircraft_id, {})
            row = dict(previous)
            if previous.get("route_key"):
                data["history"].append({
                    "at": int(time.time()), "aircraft_id": aircraft_id,
                    "registration": registration or row.get("registration", ""),
                    "action": "rota_removida_no_jogo", "previous": row["route_key"],
                })
                data["history"] = data["history"][-_MAX_HISTORY:]
            for field in ("origin", "destination", "route_key", "proposal", "profit_per_day",
                          "game_verified_at"):
                row.pop(field, None)
            row.update({
                "aircraft_id": aircraft_id,
                "registration": registration or row.get("registration", aircraft_id),
                "model": model or row.get("model", "?"),
                "status": "sem_rota",
                "at_base": True,
                "last_seen": int(time.time()),
                "grounded_confirmed_at": int(time.time()),
            })
            data["aircraft"][aircraft_id] = row
            self._save(data)
            return True

    def note(self, aircraft_id: str, status: str, *, proposal: Optional[dict] = None) -> bool:
        """Save reroute status/profit proposal without changing the verified route."""
        with _LOCK:
            data = _state(self.path)
            entry = data["aircraft"].get(str(aircraft_id))
            if not entry:
                return False
            changed = entry.get("status") != status or entry.get("proposal") != proposal
            if not changed:
                return True
            entry["status"] = status
            if proposal is None:
                entry.pop("proposal", None)
            else:
                entry["proposal"] = proposal
            data["history"].append({
                "at": int(time.time()), "aircraft_id": str(aircraft_id),
                "registration": entry.get("registration", ""),
                "action": status, "proposal": proposal,
            })
            data["history"] = data["history"][-_MAX_HISTORY:]
            self._save(data)
            return True

    def record_scan(self, visible: int, identified: int, missing_airports: int) -> None:
        """Persist the audit outcome even if no aircraft route was identified.

        Does not change any existing assignment; the panel can explain why
        the last attempt produced no new route relations.
        """
        with _LOCK:
            data = _state(self.path)
            data["last_scan"] = {
                "at": int(time.time()),
                "visible": max(0, int(visible)),
                "identified": max(0, int(identified)),
                "missing_airports": max(0, int(missing_airports)),
            }
            self._save(data)

    def snapshot(self, *, allow_duplicates: bool = True) -> dict:
        with _LOCK:
            data = deepcopy(_state(self.path))
        rows = list(data["aircraft"].values())
        rows.sort(key=lambda r: (r.get("registration", ""), r.get("aircraft_id", "")))
        duplicates: list[list[dict]] = []
        visited: set[str] = set()
        for row in rows:
            identity = row.get("aircraft_id", "")
            if identity in visited or not route_key(row.get("origin", {}), row.get("destination", {})):
                continue
            group = [other for other in rows if same_route(row, other)]
            if len(group) > 1:
                duplicates.append(group)
                visited.update(entry["aircraft_id"] for entry in group)
        duplicate_ids = {entry["aircraft_id"] for group in duplicates for entry in group}
        for row in rows:
            row["duplicate"] = row.get("aircraft_id") in duplicate_ids
        return {
            "relations": rows,
            "duplicates": [{"route": group[0].get("route_key"), "aircraft": [
                {"id": r.get("aircraft_id"), "registration": r.get("registration")} for r in group
            ]} for group in duplicates],
            "history": data["history"][-80:][::-1],
            "total": len(rows), "duplicate_routes": len(duplicates),
            "affected_aircraft": len(duplicate_ids),
            "allow_duplicates": bool(allow_duplicates),
            "last_scan": data.get("last_scan"),
            "partial": True,  # the game may expose only a page of the fleet at a time
        }

    def is_occupied(self, origin: dict, destination: dict, except_aircraft: str = "") -> bool:
        if route_key(origin, destination) is None:
            return False
        with _LOCK:
            records = _state(self.path)["aircraft"].values()
        return any(
            str(row.get("aircraft_id")) != str(except_aircraft)
            and same_route({"origin": origin, "destination": destination}, row)
            for row in records
        )
