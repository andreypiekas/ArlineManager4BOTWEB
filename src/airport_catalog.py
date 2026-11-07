"""Local offline mapping of AM4's game airport identifiers to IATA/ICAO.

No network requests or live-game mutations are performed. The compact factual
reference in assets/airports_am4_codes.csv is from a public AM4 community data
snapshot. The game's own airport-ID values still take precedence over cache
data, and every action is checked against the live game's own controls.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Airport:
    game_id: str
    iata: str
    icao: str


_DATA = Path(__file__).resolve().parents[1] / "assets" / "airports_am4_codes.csv"
_ID = re.compile(r"^[0-9]{1,12}$")
_IATA = re.compile(r"^[A-Z]{3}$")
_ICAO = re.compile(r"^[A-Z]{4}$")


@lru_cache(maxsize=1)
def _index() -> tuple[dict[str, Airport], dict[str, Airport]]:
    by_id: dict[str, Airport] = {}
    by_code: dict[str, Airport] = {}
    try:
        with _DATA.open(encoding="utf-8", newline="") as handle:
            for id_, iata, icao in csv.reader(
                row for row in handle if not row.startswith("#")
            ):
                id_, iata, icao = id_.strip(), iata.strip(), icao.strip()
                if not _ID.fullmatch(id_) or not _IATA.fullmatch(iata) or not _ICAO.fullmatch(icao):
                    continue
                airport = Airport(id_, iata, icao)
                by_id[id_] = airport
                # Ambiguous codes are intentionally not treated as unique.
                for code in (iata, icao):
                    if code in by_code and by_code[code] != airport:
                        by_code.pop(code)
                    else:
                        by_code[code] = airport
    except (FileNotFoundError, OSError, ValueError):
        pass
    return by_id, by_code


def by_id(game_id: object) -> Optional[Airport]:
    return _index()[0].get(str(game_id or "").strip())


def by_code(code: object) -> Optional[Airport]:
    return _index()[1].get(str(code or "").strip().upper())


def game_code(game_id: object, code: object = "") -> str:
    """Return an explicit live code, else a catalog code for a real game ID.

    A genuine live code always wins; the snapshot is auxiliary and may be stale.
    """
    live = str(code or "").strip().upper()
    if _IATA.fullmatch(live) or _ICAO.fullmatch(live):
        return live
    item = by_id(game_id)
    return item.iata if item else ""


def same_airport_identity(a: dict, b: dict) -> bool:
    """Confirm equivalent IATA/ICAO/ID identities while avoiding ID conflicts."""
    a_id, b_id = str(a.get("id") or ""), str(b.get("id") or "")
    if a_id and b_id:
        return a_id == b_id
    a_code = str(a.get("code") or "").strip().upper()
    b_code = str(b.get("code") or "").strip().upper()
    if not a_code or not b_code:
        item_a = by_id(a_id)
        item_b = by_id(b_id)
        a_code = a_code or (item_a.iata if item_a else "")
        b_code = b_code or (item_b.iata if item_b else "")
    if a_code == b_code and a_code:
        if a_id and by_id(a_id) and a_code not in (by_id(a_id).iata, by_id(a_id).icao):
            return False
        if b_id and by_id(b_id) and b_code not in (by_id(b_id).iata, by_id(b_id).icao):
            return False
        return True
    if not a_code or not b_code:
        return False
    airport_a, airport_b = by_code(a_code), by_code(b_code)
    if airport_a is None or airport_b is None or airport_a != airport_b:
        return False
    if a_id and airport_a.game_id != a_id:
        return False
    if b_id and airport_b.game_id != b_id:
        return False
    return True
