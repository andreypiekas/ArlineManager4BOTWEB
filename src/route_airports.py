"""Resolve game airport IDs from live, uniquely labeled hub options.

This never looks up public airport IDs or guesses from city names: the IDs
must be supplied by the authenticated game's <select id="hubSelect">.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

_CODE = re.compile(r"^[A-Z]{3,4}$")
_GAME_ID = re.compile(r"^[0-9]{1,12}$")


@dataclass(frozen=True)
class HubMatch:
    airport_id: str
    code: str
    opposite_code: str


def _code(value: object) -> str:
    code = str(value or "").upper().strip()
    return code if _CODE.fullmatch(code) else ""


def code_in_label(code: str, label: object) -> bool:
    """Match code as a separate token only (no substring/city-name guessing)."""
    code = _code(code)
    if not code:
        return False
    return bool(re.search(r"(?<![A-Z0-9])" + re.escape(code) + r"(?![A-Z0-9])",
                          str(label or "").upper()))


def match_hub_options(first_code: str, second_code: str,
                      options: Iterable[Mapping[str, object]]) -> Optional[HubMatch]:
    """Choose ONE endpoint as hub only if a unique game option confirms it.

    If both ends are hubs or if labels do not include exact codes, return None.
    This is deliberate: choosing the wrong base could alter the wrong route.
    """
    first_code, second_code = _code(first_code), _code(second_code)
    if not first_code or not second_code or first_code == second_code:
        return None
    matches = set()
    for option in options:
        ident = str(option.get("id") or "").strip()
        if not _GAME_ID.fullmatch(ident):
            continue
        label = " ".join(str(option.get(k) or "") for k in ("text", "code", "title"))
        for match, opposite in ((first_code, second_code), (second_code, first_code)):
            if code_in_label(match, label):
                matches.add((ident, match, opposite))
    if len(matches) != 1:
        return None
    ident, code, opposite = matches.pop()
    return HubMatch(ident, code, opposite)


def code_from_candidate(row: Mapping[str, object]) -> str:
    """Read a game-provided IATA/ICAO code, never infer one from a city name."""
    for key in ("code", "iata", "icao"):
        code = _code(row.get(key))
        if code:
            return code
    label = str(row.get("name") or "").strip().upper()
    # Examples: "Oslo (OSL)", "OSL - Oslo", "Oslo / OSL".
    bracketed = re.findall(r"\(([A-Z]{3,4})\)", label)
    if len(bracketed) == 1:
        return bracketed[0]
    head = re.match(r"^([A-Z]{3,4})\s*[-–|:]\s+", label)
    if head:
        return head[1]
    tail = re.search(r"\s+[/|]\s*([A-Z]{3,4})$", label)
    return tail[1] if tail else ""


def explain_hub_options(first_code: str, second_code: str,
                        options: Iterable[Mapping[str, object]]) -> dict:
    """Explain a failed game-hub lookup without guessing airport identities.

    The game's hub selector represents selectable airline hubs, not a global
    airport registry. A route endpoint may legitimately be absent from it.
    Public-facing diagnostics contain only airport selectors (no cookies,
    credentials, aircraft state, or entire HTML fragments).
    """
    options = list(options)
    matched: dict[str, list[str]] = {_code(first_code): [], _code(second_code): []}
    matched.pop("", None)
    codes_seen = 0
    valid_ids = 0
    details = []
    for opt in options:
        airport_id = str(opt.get("id") or "").strip()
        label = " ".join(str(opt.get(k) or "") for k in ("text", "code", "title")).strip()
        if not _GAME_ID.fullmatch(airport_id):
            continue
        valid_ids += 1
        declared = _code(opt.get("code"))
        text = label.upper().strip()
        # Plain four-letter city names such as "Oslo" are NOT airport codes.
        explicitly_coded = bool(
            _CODE.fullmatch(text)
            or re.search(r"\\([A-Z]{3,4}\\)", text)
            or re.search(r"(?:^|\\s)[A-Z]{3,4}\\s*[-–|/]\\s", text)
            or re.search(r"\\s[-–|/]\\s*[A-Z]{3,4}$", text)
        )
        if declared or explicitly_coded:
            codes_seen += 1
        for code in matched:
            if code_in_label(code, label):
                matched[code].append(airport_id)
        if len(details) < 5:
            # Strip control characters and cap label length.
            safe = "".join(char for char in label if char.isprintable())[:75]
            details.append(f"{airport_id}: {safe}")
    if valid_ids == 0:
        reason = "seletor_sem_ids_validos"
    elif any(len(hits) > 1 for hits in matched.values()) or sum(map(len, matched.values())) > 1:
        reason = "bases_ambiguas"
    elif sum(map(len, matched.values())) == 1:
        reason = "base_identificada"
    elif codes_seen == 0:
        reason = "etiquetas_sem_codigos_aeroportos"
    else:
        reason = "nenhuma_ponta_da_rota_nas_bases"
    return {
        "reason": reason,
        "total_options": len(options),
        "valid_ids": valid_ids,
        "labels_with_possible_codes": codes_seen,
        "matched": matched,
        "samples": details,
    }
