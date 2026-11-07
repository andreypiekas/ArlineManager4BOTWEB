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
OPTIONS_FIELDS = MARKETING_FIELDS + [("cash_sync_seconds", "Sincronizar saldo a cada (segundos)")]
TELEGRAM_FIELDS = [("summary_hour", "Horário do resumo diário (0-23)")]
ALL_FIELDS = MARKET_FIELDS + FLEET_FIELDS + AIRCRAFT_FIELDS + OPTIONS_FIELDS + TELEGRAM_FIELDS

# (options key, label) for the switches of each tab
MARKET_SWITCHES = [
    ("smart_buy", "Compra inteligente com histórico de preços"),
]
FLEET_SWITCHES = [
    ("auto_repair", "Reparar aeronaves desgastadas"),
    ("auto_check", "Programar A-checks"),
    ("auto_route", "Criar rotas para aeronaves estacionadas"),
    ("allow_duplicate_routes", "Permitir aeronaves na mesma rota (ida/volta)"),
    ("auto_hangar", "Ampliar o hangar quando estiver cheio"),
    ("auto_seats", "Assentos executiva / primeira conforme a demanda"),
    ("auto_mods", "Melhorias: velocidade, combustível e CO₂"),
]
AIRCRAFT_SWITCHES = [
    ("autobuy_aircraft", "Comprar aeronaves"),
    ("save_for_goal", "Economizar para uma aeronave desejada"),
    ("goal_invest", "Permitir compras intermediárias antes da meta"),
]
OPTION_SWITCHES = [
    ("auto_depart", "Decolar aeronaves"),
    ("selective_depart", "Despacho individual seguro quando houver rotas duplicadas"),
    ("experimental_id_batch_depart", "EXPERIMENTAL: decolagem por ID (API não verificada)"),
    ("autobuy_fuel", "Comprar combustível"),
    ("autobuy_co2", "Comprar CO₂"),
    ("auto_marketing", "Campanhas de reputação"),
    ("marketing_eco", "Campanha ecológica"),
    ("auto_checklist", "Monitorar a lista de tarefas do jogo"),
    ("start_on_launch", "Iniciar o bot ao abrir"),
    ("keep_session", "Manter a sessão do navegador"),
    ("headless", "Navegador em segundo plano (headless)"),
    ("auto_restart", "Reiniciar automaticamente após erro"),
    ("dry_run", "Simulação (sem gastos)"),
]
# Cada evento é independente. A opção "telegram" funciona como chave geral.
# Defaults preservam o comportamento de instalações existentes.
TELEGRAM_SWITCHES = [
    ("telegram", "Ativar notificações do Telegram"),
    ("telegram_errors", "Erros e interrupções"),
    ("telegram_status", "Início e parada do bot"),
    ("telegram_daily", "Resumo diário"),
    ("telegram_departures", "Decolagens"),
    ("telegram_fuel", "Compras de combustível"),
    ("telegram_co2", "Compras de CO₂"),
    ("telegram_routes", "Rotas criadas"),
    ("telegram_aircraft", "Compras de aeronaves"),
    ("telegram_maintenance", "Reparos e A-checks"),
    ("telegram_hangar", "Ampliações do hangar"),
    ("telegram_workshop", "Oficina: assentos e melhorias"),
    ("telegram_marketing", "Campanhas de marketing"),
    ("telegram_checklist", "Recompensas e tarefas"),
    ("telegram_simulation", "Eventos da simulação"),
]
ALL_SWITCHES = MARKET_SWITCHES + FLEET_SWITCHES + AIRCRAFT_SWITCHES + OPTION_SWITCHES + TELEGRAM_SWITCHES

# Configurações de modelos e metas (aba Aeronaves)
TEXT_SETTINGS = [
    ("goal_model", "Modelo da compra automática"),
    ("aircraft_model", "Modelo fixo (sem meta ativa)"),
    ("engine_preference", "Motorização da aeronave"),
]

# Tabs in display order: (name, icon, fields, switches)
TABS = [
    ("Mercado", "🛒", MARKET_FIELDS, MARKET_SWITCHES),
    ("Frota", "🛩️", FLEET_FIELDS, FLEET_SWITCHES),
    ("Aeronaves", "✈️", AIRCRAFT_FIELDS, AIRCRAFT_SWITCHES),
    ("Opções", "⚙️", OPTIONS_FIELDS, OPTION_SWITCHES),
    ("Telegram", "📨", TELEGRAM_FIELDS, TELEGRAM_SWITCHES),
]

# Switches that default to on when the key is missing from config/defaults.ini too (tests/ keep both in step)
OPTION_DEFAULTS = {"auto_restart": True, "auto_hangar": True, "goal_invest": True, "auto_seats": True, "auto_mods": True,
                   "auto_marketing": True, "marketing_eco": True, "auto_checklist": True}

_LIMITS = {
    "summary_hour": (0, 23),
    "cash_sync_seconds": (30, 600),
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
