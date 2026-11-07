"""Seleção de motorização antes de encomendar uma aeronave.

O jogo pode alterar seu HTML. Apenas campos nativos identificados claramente
como motores são utilizados; qualquer ambiguidade impede a compra. Nunca
confirmamos uma aquisição quando o motor solicitado não foi verificado.
"""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot

log = logging.getLogger("am4bot.aviones")

# Leitura não intrusiva. Nenhum clique nem alteração de campos nesta etapa.
# Nomes técnicos internos são preservados: o jogo não depende do idioma.
_ENGINE_OPTIONS_JS = r"""
const root = document.querySelector('#acModel');
if (!root) return [];
const engine = /(engine|motor|motoriz|moteur)/i;
const labelOf = el => {
  const id = el.id || '';
  const explicit = id && Array.from(root.querySelectorAll('label[for]')).find(x => x.htmlFor === id);
  const wrap = el.closest('label');
  const group = el.closest('.form-group, fieldset, .input-group');
  return [(explicit || wrap)?.textContent || '', group?.querySelector('legend, label')?.textContent || '',
          el.getAttribute('aria-label') || '', el.name || '', id].join(' ').trim();
};
const dataNum = (el, key) => {
  const value = el.getAttribute('data-' + key);
  if (!value || !/^\d+(\.\d+)?$/.test(value)) return null;
  return Number(value);
};
const groups = [];
for (const el of root.querySelectorAll('select')) {
  const context = labelOf(el);
  if (!engine.test(context)) continue;
  const options = Array.from(el.options).map(o => ({
    value: o.value, label: (o.textContent || '').trim(),
    speed: dataNum(o, 'speed'), fuel: dataNum(o, 'fuel'),
    selected: o.selected, disabled: o.disabled || !o.value
  })).filter(o => o.label && !/^(select|selecione|choose|seleccione)\b/i.test(o.label));
  if (options.length) groups.push({type:'select', name:el.name || '', id:el.id || '', options});
}
const radios = Array.from(root.querySelectorAll('input[type="radio"]'));
for (const name of new Set(radios.map(el => el.name).filter(Boolean))) {
  const items = radios.filter(el => el.name === name);
  const context = items.map(labelOf).join(' ');
  if (!engine.test(context)) continue;
  const options = items.map(el => {
    const explicit = el.id && Array.from(root.querySelectorAll('label[for]')).find(x => x.htmlFor === el.id);
    const label = (explicit || el.closest('label'))?.textContent?.trim() ||
                  el.getAttribute('aria-label') || el.value;
    return {value:el.value, label:label.trim(), speed:dataNum(el,'speed'),
            fuel:dataNum(el,'fuel'), selected:el.checked, disabled:el.disabled};
  });
  groups.push({type:'radio', name, id:'', options});
}
return groups;
"""

# Seleciona APENAS a opção identificada na leitura acima. Não clica no botão
# de compra. A verificação de seleção é feita em nova leitura posteriormente.
_SET_ENGINE_JS = r"""
const root = document.querySelector('#acModel');
if (!root) return false;
const kind = arguments[0], identifier = arguments[1], optionValue = arguments[2];
if (kind === 'select') {
  const nodes = Array.from(root.querySelectorAll('select'));
  const matches = nodes.filter(el => el.id === identifier || el.name === identifier);
  if (matches.length !== 1) return false;
  const el = matches[0];
  const option = Array.from(el.options).find(o => o.value === optionValue && !o.disabled);
  if (!option) return false;
  el.value = optionValue;
  el.dispatchEvent(new Event('input', {bubbles:true}));
  el.dispatchEvent(new Event('change', {bubbles:true}));
  return el.value === optionValue;
}
if (kind === 'radio') {
  const nodes = Array.from(root.querySelectorAll('input[type="radio"]'))
                     .filter(el => el.name === identifier && el.value === optionValue && !el.disabled);
  if (nodes.length !== 1) return false;
  nodes[0].click();
  return nodes[0].checked;
}
return false;
"""


class EngineSelectionError(ValueError):
    """Seleção de motor incerta. Nunca prosseguir com a compra."""


@dataclass(frozen=True)
class EngineChoice:
    label: str
    value: str
    speed: float | None
    fuel: float | None
    selected: bool
    disabled: bool


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold().strip()


def parse_preference(value: str) -> tuple[str, str]:
    preference = (value or "").strip()
    if preference in ("", "default"):
        return "default", ""
    if preference in ("fastest", "economical"):
        return preference, ""
    if preference.startswith("name:"):
        name = preference[5:].strip()
        if not name or len(name) > 75:
            raise EngineSelectionError("Informe o nome do motor específico (máximo de 75 caracteres).")
        return "name", name
    raise EngineSelectionError("Preferência de motor inválida. Use padrão, mais rápido, econômico ou nome específico.")


def validate_preference(value: str) -> str:
    """Devolve a preferência canônica; usado pelas interfaces ao salvar."""
    mode, name = parse_preference(value)
    return f"name:{name}" if mode == "name" else mode


def choose_engine(groups: list[dict], preference: str) -> tuple[dict, EngineChoice]:
    mode, name = parse_preference(preference)
    if mode == "default":
        raise EngineSelectionError("O motor padrão não requer seleção explícita.")
    if len(groups) != 1:
        raise EngineSelectionError(
            f"Esperava um único seletor de motorização na compra; encontrei {len(groups)}. "
            "Compra bloqueada para evitar motor incorreto."
        )
    group = groups[0]
    if group.get("type") not in ("select", "radio"):
        raise EngineSelectionError("Tipo de seletor de motor desconhecido.")
    ident = group.get("id") if group["type"] == "select" and group.get("id") else group.get("name")
    if not ident:
        raise EngineSelectionError("O seletor de motor não tem identificador estável.")
    available = [
        EngineChoice(str(x.get("label", "")).strip(), str(x.get("value", "")),
                     _positive_number(x.get("speed")), _positive_number(x.get("fuel")),
                     x.get("selected") is True, x.get("disabled") is True)
        for x in group.get("options", [])
        if x.get("label") and str(x.get("value", "")) and x.get("disabled") is not True
    ]
    if not available or len({o.value for o in available}) != len(available):
        raise EngineSelectionError("Lista de motores vazia ou ambígua; compra não realizada.")
    if mode == "name":
        exact = [o for o in available if normalize(o.label) == normalize(name)]
        matches = exact if exact else [o for o in available if normalize(name) in normalize(o.label)]
        if len(matches) != 1:
            raise EngineSelectionError(
                f"Motor «{name}» não identificado de forma única. "
                "Opções detectadas: " + ", ".join(o.label[:60] for o in available)
            )
        choice = matches[0]
    elif mode == "fastest":
        if any(o.speed is None for o in available):
            raise EngineSelectionError(
                "O jogo não expôs velocidade comparável em todas as opções; "
                "não vou escolher o motor mais rápido por suposição."
            )
        choice = max(available, key=lambda o: (o.speed, -(o.fuel or float("inf"))))
    else:
        if any(o.fuel is None for o in available):
            raise EngineSelectionError(
                "O jogo não expôs consumo comparável em todas as opções; "
                "não vou escolher o motor mais econômico por suposição."
            )
        choice = min(available, key=lambda o: (o.fuel, -(o.speed or 0)))
    return group, choice


def _positive_number(value: object) -> float | None:
    try:
        number = float(value)
        return number if 0 < number < 1e9 else None
    except (ValueError, TypeError):
        return None


def prepare_engine(bot: "Bot", preference: str) -> str | None:
    """Escolhe e confirma o motor. Em simulação, informa a opção sem clicar.

    Retorna o nome confirmado ou None quando o jogo mantém o padrão antigo.
    Em falhas lança EngineSelectionError (order_aircraft interrompe a compra).
    """
    mode, _ = parse_preference(preference)
    if mode == "default":
        return None
    groups = bot.js(_ENGINE_OPTIONS_JS) or []
    if not isinstance(groups, list):
        raise EngineSelectionError("O jogo não retornou uma lista válida de motores.")
    group, choice = choose_engine(groups, preference)
    log.info("Motorização para a próxima compra: %s (%s).", choice.label, mode)
    if bot.dry_run:
        log.info("[SIMULAÇÃO] Selecionaria o motor %s sem alterar o jogo.", choice.label)
        return choice.label
    identifier = group.get("id") if group["type"] == "select" and group.get("id") else group["name"]
    if not bot.js(_SET_ENGINE_JS, group["type"], identifier, choice.value):
        raise EngineSelectionError("Não consegui selecionar o motor solicitado; compra bloqueada.")
    # Atualizações do jogo podem recriar os elementos: verificar novamente o estado.
    bot.pause(0.4, 0.8)
    new_groups = bot.js(_ENGINE_OPTIONS_JS) or []
    if len(new_groups) != 1:
        raise EngineSelectionError("O seletor de motores desapareceu após a escolha.")
    selected = [o for o in new_groups[0].get("options", []) if o.get("selected") is True]
    if len(selected) != 1 or str(selected[0].get("value")) != choice.value:
        raise EngineSelectionError("O jogo não confirmou o motor solicitado; compra cancelada.")
    log.info("Motor confirmado no formulário de compra: %s.", choice.label)
    return choice.label
