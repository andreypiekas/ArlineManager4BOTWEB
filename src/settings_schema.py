"""What the user can change, shared by the desktop window and the web dashboard (labels in Brazilian Portuguese).

Numbers live in [settings], switches in [options] (defaults in config/defaults.ini, changes in settings.ini). Both interfaces build their
tabs from these lists, so a new setting only has to be added here (and to help_texts.HELP).
"""
from __future__ import annotations

# (settings key, label) for the whole-number fields of each tab
MARKET_FIELDS = [
    ("fuel_price_good", "Comprar combustível a ≤ $"),
    ("co2_price_good", "Comprar CO₂ a ≤ $"),
    ("min_stock_pct", "Estoque mínimo (%)"),
    ("stock_days", "Estoque máximo (dias)"),
    ("market_max_spend_pct", "Gasto máximo (% do saldo)"),
    ("cycle_min_minutes", "Intervalo mínimo (min)"),
    ("cycle_max_minutes", "Intervalo máximo (min)"),
    ("buy_percentile", "Percentil de compra (%)"),
    ("excellent_percentile", "Percentil excepcional (%)"),
    ("history_days", "Histórico (dias)"),
    ("fuel_quantity_buy", "Máx. combustível por compra"),
    ("co2_quantity_buy", "Máx. CO₂ por compra"),
]
FLEET_FIELDS = [
    ("repair_wear_pct", "Reparar a partir de desgaste (%)"),
    ("check_hours_min", "A-check quando restarem ≤ horas"),
    ("cash_reserve", "Reserva de caixa ($)"),
    ("route_max_distance", "Rota máxima para aeronave pequena (km)"),
    ("route_max_distance_big", "Rota máxima para aeronave grande (km)"),
    ("route_min_runway", "Pista mínima (pés)"),
    ("hangar_min_free", "Vagas disponíveis no hangar"),
    ("fleet_actions_per_cycle", "Rotas / pedidos por ciclo"),
    ("seats_max_payback", "Oficina: retorno em até ≤ dias"),
]
AIRCRAFT_FIELDS = [
    ("aircraft_max_price", "Preço máximo sem meta (0 = livre)"),
]
MARKETING_FIELDS = [
    ("marketing_campaign", "Campanha de reputação (1-4)"),
    ("marketing_hours", "Duração da campanha (h)"),
]
OPTIONS_FIELDS = MARKETING_FIELDS + [
    ("summary_hour", "Horário do resumo diário (0-23)"),
]
ALL_FIELDS = MARKET_FIELDS + FLEET_FIELDS + AIRCRAFT_FIELDS + OPTIONS_FIELDS

# (options key, label) for the switches of each tab
MARKET_SWITCHES = [
    ("smart_buy", "Compra inteligente com histórico de preços"),
]
FLEET_SWITCHES = [
    ("auto_repair", "Reparar aeronaves desgastadas"),
    ("auto_check", "Programar A-checks"),
    ("auto_route", "Criar rotas para aeronaves estacionadas"),
    ("auto_hangar", "Ampliar o hangar quando estiver cheio"),
    ("auto_seats", "Assentos executiva / primeira conforme a demanda"),
    ("auto_mods", "Melhorias: velocidade, combustível e CO₂"),
]
AIRCRAFT_SWITCHES = [
    ("autobuy_aircraft", "Comprar aeronaves"),
    ("save_for_goal", "Economizar para uma aeronave desejada"),
    ("goal_invest", "Investir em aeronaves menores se anteciparem a meta"),
]
OPTION_SWITCHES = [
    ("auto_depart", "Decolar aeronaves"),
    ("autobuy_fuel", "Comprar combustível"),
    ("autobuy_co2", "Comprar CO₂"),
    ("auto_marketing", "Campanhas de reputação"),
    ("marketing_eco", "Campanha ecológica"),
    ("auto_checklist", "Monitorar a lista de tarefas do jogo"),
    ("start_on_launch", "Iniciar o bot ao abrir"),
    ("keep_session", "Manter a sessão do navegador"),
    ("headless", "Navegador em segundo plano (headless)"),
    ("telegram", "Notificações pelo Telegram"),
    ("telegram_departures", "Telegram: avisar também as decolagens"),
    ("auto_restart", "Reiniciar automaticamente após erro"),
    ("dry_run", "Simulação (sem gastos)"),
]
ALL_SWITCHES = MARKET_SWITCHES + FLEET_SWITCHES + AIRCRAFT_SWITCHES + OPTION_SWITCHES

# Free-text settings (Aviones tab)
TEXT_SETTINGS = [
    ("goal_model", "Aeronave desejada"),
    ("aircraft_model", "Modelo fixo sem meta"),
]

# Tabs in display order: (name, icon, fields, switches)
TABS = [
    ("Mercado", "🛒", MARKET_FIELDS, MARKET_SWITCHES),
    ("Flota", "🛩️", FLEET_FIELDS, FLEET_SWITCHES),
    ("Aviones", "✈️", AIRCRAFT_FIELDS, AIRCRAFT_SWITCHES),
    ("Opciones", "⚙️", OPTIONS_FIELDS, OPTION_SWITCHES),
]

# Switches that default to on when the key is missing from config/defaults.ini too (tests/ keep both in step)
OPTION_DEFAULTS = {"auto_restart": True, "auto_hangar": True, "goal_invest": True, "auto_seats": True, "auto_mods": True,
                   "auto_marketing": True, "marketing_eco": True, "auto_checklist": True}

_LIMITS = {
    "summary_hour": (0, 23),
    "marketing_campaign": (1, 4),
    "marketing_hours": (4, 24),
    "cycle_min_minutes": (1, None),
}


def parse_int(raw) -> int | None:
    """'200,000' / '200.000' / 200000 -> 200000; None when it is not a whole number."""
    text = str(raw).strip().replace(",", "").replace(".", "")
    return int(text) if text.isdigit() else None


def clamp_settings(values: dict[str, int]) -> dict[str, int]:
    """Keep the numbers inside the ranges the bot understands (in place, also returned)."""
    for key, (low, high) in _LIMITS.items():
        if key in values:
            values[key] = max(low, values[key]) if high is None else max(low, min(high, values[key]))
    if "cycle_max_minutes" in values and "cycle_min_minutes" in values:
        values["cycle_max_minutes"] = max(values["cycle_max_minutes"], values["cycle_min_minutes"])
    return values
