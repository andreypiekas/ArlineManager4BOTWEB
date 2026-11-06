"""Desktop and web interface languages: Brazilian Portuguese (default) and English.

Upstream Spanish text remains supported as an internal lookup key for backwards
compatibility. PT_BR translates it to Portuguese; EN translates it to English.
Formatted texts preserve their named placeholders. Tooltips use help_texts.py.
"""

from __future__ import annotations

LANGUAGES = {"pt_BR": "Português (Brasil)", "en": "English"}
DEFAULT_LANGUAGE = "pt_BR"
_language = DEFAULT_LANGUAGE


def set_language(code: str) -> str:
    global _language
    _language = code if code in LANGUAGES else DEFAULT_LANGUAGE
    return _language


def language() -> str:
    return _language


def t(text: str, **values) -> str:
    result = EN.get(text, EN.get(PT_TO_ES.get(text, ""), text)) if _language == "en" else PT_BR.get(text, text)
    return result.format(**values) if values else result


def tip(key: str):
    """Hover help of a setting or control in the current language (None if there is none)."""
    from help_texts import HELP, HELP_EN
    return (HELP_EN if _language == "en" else HELP).get(key) or HELP.get(key)


EN: dict[str, str] = {
    # ---- settings (settings_schema.py) and tabs
    "Mercado": "Market", "Flota": "Fleet", "Aviones": "Aircraft", "Opciones": "Options",
    "Comprar fuel a ≤ $": "Buy fuel at ≤ $", "Comprar CO2 a ≤ $": "Buy CO2 at ≤ $",
    "Stock mínimo (%)": "Minimum stock (%)", "Stock máx. (días)": "Max. stock (days)",
    "Gasto máx. (% caja)": "Max. spend (% of cash)",
    "Espera mín. (min)": "Min. wait (min)", "Espera máx. (min)": "Max. wait (min)",
    "Percentil compra (%)": "Buy percentile (%)", "Percentil excepc. (%)": "Exceptional pctl. (%)",
    "Histórico (días)": "History (days)", "Máx. fuel / compra": "Max. fuel / purchase",
    "Máx. CO2 / compra": "Max. CO2 / purchase",
    "Reparar a partir de desgaste (%)": "Repair from wear (%)", "A-check si quedan <= horas": "A-check at <= hours left",
    "Reserva de caja ($)": "Cash reserve ($)", "Ruta máx. avión pequeño (km)": "Max. route, small aircraft (km)",
    "Ruta máx. avión grande (km)": "Max. route, big aircraft (km)", "Pista mínima (ft)": "Minimum runway (ft)",
    "Huecos libres en el hangar": "Free hangar slots", "Rutas / pedidos por ciclo": "Routes / orders per cycle",
    "Taller: amortizar en ≤ días": "Workshop: pay back in ≤ days",
    "Mejoras de avión: velocidad, fuel y CO2": "Aircraft upgrades: speed, fuel and CO2",
    "Precio máx. sin objetivo (0 = libre)": "Max. price without goal (0 = any)",
    "Campaña de reputación (1-4)": "Reputation campaign (1-4)", "Duración de la campaña (h)": "Campaign length (h)",
    "Hora del resumen diario (0-23)": "Daily summary hour (0-23)",
    "Compra inteligente con el histórico de precios": "Smart buying with the price history",
    "Reparar aviones desgastados": "Repair worn aircraft", "Planificar A-checks": "Plan A-checks",
    "Crear rutas para aviones aparcados": "Create routes for parked aircraft",
    "Ampliar el hangar si se llena": "Expand the hangar when it fills up",
    "Asientos business / first según demanda": "Business / first seats by demand",
    "Comprar aviones": "Buy aircraft", "Ahorrar para un avión objetivo": "Save for a goal aircraft",
    "Invertir en pequeños si adelantan el objetivo": "Buy small ones if they bring the goal closer",
    "Despegar aviones": "Depart aircraft", "Comprar fuel": "Buy fuel", "Comprar CO2": "Buy CO2",
    "Campañas de reputación": "Reputation campaigns", "Campaña eco-friendly": "Eco-friendly campaign",
    "Vigilar el checklist del juego": "Watch the game checklist", "Iniciar el bot al abrir": "Start the bot on launch",
    "Mantener sesión del navegador": "Keep the browser session", "Navegador oculto (headless)": "Hidden browser (headless)",
    "Notificaciones por Telegram": "Telegram notifications", "Telegram: también los despegues": "Telegram: departures too",
    "Reiniciar solo tras un error": "Restart by itself after an error", "Simulación (no gasta nada)": "Dry run (spends nothing)",
    "Avión objetivo": "Goal aircraft", "Modelo fijo sin objetivo": "Fixed model without goal",
    # ---- sidebar
    "PERFIL": "PROFILE", "➕ Nuevo perfil…": "➕ New profile…", "CUENTA": "ACCOUNT", "Correo": "E-mail",
    "Contraseña": "Password", "Recordar credenciales": "Remember credentials", "▶  INICIAR BOT": "▶  START BOT",
    "■  PARAR BOT": "■  STOP BOT", "⟳  Ejecutar ciclo ahora": "⟳  Run a cycle now", "ESTADO": "STATUS",
    "APARIENCIA": "APPEARANCE", "IDIOMA": "LANGUAGE", "Claro": "Light", "Oscuro": "Dark", "Sistema": "System",
    "Juego en modo {mode}": "Game in {mode} mode", "fácil": "easy", "realista": "realism",
    "🌐  Abrir el panel web": "🌐  Open the web dashboard",
    "Abre {url} en el navegador: las mismas estadísticas, registro y ajustes.":
        "Opens {url} in the browser: the same statistics, log and settings.",
    "Próxima revisión en {time}": "Next check in {time}", "Revisando ...": "Checking ...",
    "Reinicio automático en {time}": "Automatic restart in {time}",
    "Nuevo perfil": "New profile",
    "Nombre del perfil nuevo (por ejemplo «realismo»).\nTendrá su propia cuenta, ajustes, datos y panel web.":
        "Name of the new profile (for example “realism”).\nIt gets its own account, settings, data and web dashboard.",
    # ---- bot states (bot.BotState values)
    "Parado": "Stopped", "Abriendo navegador": "Opening browser", "Iniciando sesión": "Logging in",
    "En marcha": "Running", "Parando": "Stopping", "Error": "Error",
    # ---- tiles
    "💰  DINERO": "💰  MONEY", "⭐  REPUTACIÓN": "⭐  REPUTATION", "⛽  FUEL": "⛽  FUEL", "🌿  CO2": "🌿  CO2",
    "🛩  FLOTA": "🛩  FLEET", "🎯  OBJETIVO": "🎯  GOAL",
    "+{money}/día": "+{money}/day", "{n} puntos": "{n} points", "campaña {time}": "campaign {time}",
    "sin campaña activa": "no campaign running", "compra ≤ {price}": "buy ≤ {price}", "{n} en vuelo": "{n} flying",
    "{n} aparc.": "{n} parked", "{n} pend.": "{n} pending", "actualizado {time}": "updated {time}",
    "Sin datos todavía": "No data yet",
    # ---- tabs
    "Guardar ajustes": "Save settings", "vacío = más rentable": "empty = most profitable",
    "(mín. visto ${price})": "(lowest seen ${price})",
    "Precio más bajo visto: ${price} el %d/%m/%Y a las %H:%M": "Lowest price seen: ${price} on %d/%m/%Y at %H:%M",
    "Probar Telegram": "Test Telegram",
    "Telegram configurado para el chat {chat} (config/secrets.ini).": "Telegram set up for chat {chat} (config/secrets.ini).",
    "Telegram sin configurar: añade bot_token y chat_id en la sección [telegram] de config/secrets.ini.":
        "Telegram not set up: add bot_token and chat_id to the [telegram] section of config/secrets.ini.",
    # ---- goal panel
    "🎯 Sin objetivo": "🎯 No goal", "🎯 Elige un avión objetivo": "🎯 Pick a goal aircraft",
    "Escribe o elige un modelo en «Avión objetivo» y pulsa Guardar ajustes.":
        "Type or pick a model in “Goal aircraft” and press Save settings.",
    "No encuentro ese modelo en el mercado guardado. Revisa el nombre o espera a que el bot consulte el mercado.":
        "That model is not in the saved market. Check the name or wait until the bot reads the market.",
    "Ahorrado {have} ({pct}%), la reserva aparte.": "Saved {have} ({pct}%), the reserve kept apart.",
    "¡Ya llega! Lo pedirá en la próxima revisión si hay hueco en el hangar.":
        "Enough! It is ordered at the next check if the hangar has room.",
    "Faltan {missing} · {rate} · llegada {eta}": "{missing} to go · {rate} · arrives {eta}",
    "{money}/día": "{money}/day", "ritmo aún sin medir": "rate not measured yet",
    "Hangar: {free} huecos libres de {total}": "Hangar: {free} free slots of {total}",
    "Modo ahorro apagado: compra el avión más rentable que pueda.": "Savings mode off: buys the most profitable aircraft it can.",
    "Compra pequeños solo si se amortizan antes de llegar.": "Buys small ones only if they pay back before the goal.",
    "Solo ahorra: no compra otros aviones.": "Only saves: buys no other aircraft.",
    "IDEAS DE OBJETIVO · precio · plazas · rentabilidad estimada · llegada a tu ritmo":
        "GOAL IDEAS · price · seats · estimated profit · arrival at your pace",
    "Escalera (a tu ritmo actual y al crecer):": "Ladder (at your current pace and as you grow):",
    "Caprichos:": "Dream aircraft:",
    "{name} · {price} · {seats} pax · gana {profit}/día · se paga en {days} d":
        "{name} · {price} · {seats} pax · earns {profit}/day · pays back in {days} d",
    "El bot guardará la lista del mercado la próxima vez que lo consulte.":
        "The bot saves the market list the next time it reads it.",
    "Automático (escalera)": "Automatic (ladder)", "Automático": "Automatic", "Auto: {name}": "Auto: {name}",
    "sin estimar": "not estimated", "ya": "now", "menos de 1 h": "under 1 h", "~{n} días": "~{n} days",
    # ---- log panel
    "📜  Registro": "📜  Log", "Abrir fichero": "Open file", "Limpiar": "Clear",
    # ---- web API answers
    "El bot ya está en marcha.": "The bot is already running.", "Iniciando el bot ...": "Starting the bot ...",
    "El bot ya está parado.": "The bot is already stopped.", "Parando ...": "Stopping ...",
    "Revisando ahora.": "Checking now.", "Cerrando ...": "Closing ...", "Acción desconocida.": "Unknown action.",
    "Guardado.": "Saved.", "«{key}» debe ser un número entero.": "“{key}” must be a whole number.",
    "Ajuste desconocido «{key}».": "Unknown setting “{key}”.",
}


# Brazilian Portuguese equivalents for legacy interface strings.
PT_BR: dict[str, str] = {
    "Flota": "Frota",
    "Aviones": "Aeronaves",
    "Opciones": "Opções",
    "Comprar fuel a ≤ $": "Comprar combustível a ≤ $",
    "Comprar CO2 a ≤ $": "Comprar CO₂ a ≤ $",
    "Stock mínimo (%)": "Estoque mínimo (%)",
    "Stock máx. (días)": "Estoque máximo (dias)",
    "Gasto máx. (% caja)": "Gasto máximo (% do saldo)",
    "Espera mín. (min)": "Intervalo mínimo (min)",
    "Espera máx. (min)": "Intervalo máximo (min)",
    "Percentil compra (%)": "Percentil de compra (%)",
    "Percentil excepc. (%)": "Percentil excepcional (%)",
    "Histórico (días)": "Histórico (dias)",
    "Máx. fuel / compra": "Máx. combustível por compra",
    "Máx. CO2 / compra": "Máx. CO₂ por compra",
    "A-check si quedan <= horas": "A-check quando restarem ≤ horas",
    "Reserva de caja ($)": "Reserva de caixa ($)",
    "Ruta máx. avión pequeño (km)": "Rota máxima para aeronave pequena (km)",
    "Ruta máx. avión grande (km)": "Rota máxima para aeronave grande (km)",
    "Pista mínima (ft)": "Pista mínima (pés)",
    "Huecos libres en el hangar": "Vagas disponíveis no hangar",
    "Taller: amortizar en ≤ días": "Oficina: retorno em até ≤ dias",
    "Mejoras de avión: velocidad, fuel y CO2": "Melhorias: velocidade, combustível e CO₂",
    "Precio máx. sin objetivo (0 = libre)": "Preço máximo sem meta (0 = livre)",
    "Campaña de reputación (1-4)": "Campanha de reputação (1-4)",
    "Duración de la campaña (h)": "Duração da campanha (h)",
    "Hora del resumen diario (0-23)": "Horário do resumo diário (0-23)",
    "Compra inteligente con el histórico de precios": "Compra inteligente com histórico de preços",
    "Reparar aviones desgastados": "Reparar aeronaves desgastadas",
    "Crear rutas para aviones aparcados": "Criar rotas para aeronaves estacionadas",
    "Ampliar el hangar si se llena": "Ampliar o hangar quando estiver cheio",
    "Asientos business / first según demanda": "Assentos executiva / primeira conforme a demanda",
    "Comprar aviones": "Comprar aeronaves",
    "Ahorrar para un avión objetivo": "Economizar para uma aeronave desejada",
    "Invertir en pequeños si adelantan el objetivo": "Investir em aeronaves menores se anteciparem a meta",
    "Despegar aviones": "Decolar aeronaves",
    "Comprar fuel": "Comprar combustível",
    "Comprar CO2": "Comprar CO₂",
    "Campañas de reputación": "Campanhas de reputação",
    "Campaña eco-friendly": "Campanha ecológica",
    "Vigilar el checklist del juego": "Monitorar a lista de tarefas do jogo",
    "Iniciar el bot al abrir": "Iniciar o bot ao abrir",
    "Mantener sesión del navegador": "Manter a sessão do navegador",
    "Navegador oculto (headless)": "Navegador em segundo plano (headless)",
    "Notificaciones por Telegram": "Notificações pelo Telegram",
    "Telegram: también los despegues": "Telegram: avisar também as decolagens",
    "Reiniciar solo tras un error": "Reiniciar automaticamente após erro",
    "Simulación (no gasta nada)": "Simulação (sem gastos)",
    "Avión objetivo": "Aeronave desejada",
    "Modelo fijo sin objetivo": "Modelo fixo sem meta",
    "➕ Nuevo perfil…": "➕ Novo perfil…",
    "CUENTA": "CONTA",
    "Correo": "E-mail",
    "Contraseña": "Senha",
    "Recordar credenciales": "Lembrar credenciais",
    "⟳  Ejecutar ciclo ahora": "⟳  Executar ciclo agora",
    "ESTADO": "STATUS",
    "APARIENCIA": "APARÊNCIA",
    "Oscuro": "Escuro",
    "Juego en modo {mode}": "Jogo no modo {mode}",
    "🌐  Abrir el panel web": "🌐  Abrir o painel web",
    "Abre {url} en el navegador: las mismas estadísticas, registro y ajustes.": "Abra {url} no navegador para ver as mesmas estatísticas, registros e configurações.",
    "Próxima revisión en {time}": "Próxima verificação em {time}",
    "Revisando ...": "Verificando ...",
    "Reinicio automático en {time}": "Reinício automático em {time}",
    "Nuevo perfil": "Novo perfil",
    "Nombre del perfil nuevo (por ejemplo «realismo»).\nTendrá su propia cuenta, ajustes, datos y panel web.": "Nome do novo perfil (por exemplo, «realismo»).\nEle terá sua própria conta, configurações, dados e painel web.",
    "Abriendo navegador": "Abrindo navegador",
    "Iniciando sesión": "Fazendo login",
    "En marcha": "Em execução",
    "Error": "Erro",
    "💰  DINERO": "💰  DINHEIRO",
    "⭐  REPUTACIÓN": "⭐  REPUTAÇÃO",
    "⛽  FUEL": "⛽  COMBUSTÍVEL",
    "🌿  CO2": "🌿  CO₂",
    "🛩  FLOTA": "🛩  FROTA",
    "🎯  OBJETIVO": "🎯  META",
    "+{money}/día": "+{money}/dia",
    "{n} puntos": "{n} pontos",
    "campaña {time}": "campanha {time}",
    "sin campaña activa": "sem campanha ativa",
    "{n} en vuelo": "{n} em voo",
    "{n} aparc.": "{n} estacionadas",
    "{n} pend.": "{n} pendentes",
    "actualizado {time}": "atualizado {time}",
    "Sin datos todavía": "Ainda sem dados",
    "Guardar ajustes": "Salvar configurações",
    "vacío = más rentable": "vazio = mais rentável",
    "(mín. visto ${price})": "(menor preço registrado ${price})",
    "Precio más bajo visto: ${price} el %d/%m/%Y a las %H:%M": "Menor preço registrado: ${price} em %d/%m/%Y às %H:%M",
    "Probar Telegram": "Testar Telegram",
    "Telegram configurado para el chat {chat} (config/secrets.ini).": "Telegram configurado para o chat {chat} (config/secrets.ini).",
    "Telegram sin configurar: añade bot_token y chat_id en la sección [telegram] de config/secrets.ini.": "Telegram não configurado: informe bot_token e chat_id na seção [telegram] de config/secrets.ini.",
    "🎯 Sin objetivo": "🎯 Sem meta",
    "🎯 Elige un avión objetivo": "🎯 Escolha uma aeronave desejada",
    "Escribe o elige un modelo en «Avión objetivo» y pulsa Guardar ajustes.": "Digite ou selecione um modelo em «Aeronave desejada» e clique em Salvar configurações.",
    "No encuentro ese modelo en el mercado guardado. Revisa el nombre o espera a que el bot consulte el mercado.": "Modelo não encontrado no mercado salvo. Confira o nome ou aguarde a próxima consulta ao mercado.",
    "Ahorrado {have} ({pct}%), la reserva aparte.": "Economizado {have} ({pct}%), sem contar a reserva.",
    "¡Ya llega! Lo pedirá en la próxima revisión si hay hueco en el hangar.": "Meta alcançada! O pedido será feito na próxima verificação se houver vaga no hangar.",
    "Faltan {missing} · {rate} · llegada {eta}": "Faltam {missing} · {rate} · previsão {eta}",
    "{money}/día": "{money}/dia",
    "ritmo aún sin medir": "ritmo ainda não calculado",
    "Hangar: {free} huecos libres de {total}": "Hangar: {free} vagas disponíveis de {total}",
    "Modo ahorro apagado: compra el avión más rentable que pueda.": "Modo economia desligado: compra a aeronave mais rentável disponível.",
    "Compra pequeños solo si se amortizan antes de llegar.": "Compra aeronaves menores apenas se houver retorno antes da meta.",
    "Solo ahorra: no compra otros aviones.": "Apenas economiza: não compra outras aeronaves.",
    "IDEAS DE OBJETIVO · precio · plazas · rentabilidad estimada · llegada a tu ritmo": "SUGESTÕES DE META · preço · assentos · lucro estimado · previsão",
    "Escalera (a tu ritmo actual y al crecer):": "Progressão (no ritmo atual e com crescimento):",
    "Caprichos:": "Aeronaves dos sonhos:",
    "{name} · {price} · {seats} pax · gana {profit}/día · se paga en {days} d": "{name} · {price} · {seats} pax · rende {profit}/dia · retorno em {days} dias",
    "El bot guardará la lista del mercado la próxima vez que lo consulte.": "O bot salvará a lista do mercado na próxima consulta.",
    "Automático (escalera)": "Automático (progressão)",
    "Auto: {name}": "Automático: {name}",
    "sin estimar": "sem estimativa",
    "ya": "agora",
    "menos de 1 h": "menos de 1 h",
    "~{n} días": "~{n} dias",
    "📜  Registro": "📜  Registros",
    "Abrir fichero": "Abrir arquivo",
    "Limpiar": "Limpar",
    "El bot ya está en marcha.": "O bot já está em execução.",
    "Iniciando el bot ...": "Iniciando o bot ...",
    "El bot ya está parado.": "O bot já está parado.",
    "Revisando ahora.": "Verificando agora.",
    "Cerrando ...": "Fechando ...",
    "Acción desconocida.": "Ação desconhecida.",
    "Guardado.": "Salvo.",
    "«{key}» debe ser un número entero.": "«{key}» deve ser um número inteiro.",
    "Ajuste desconocido «{key}».": "Configuração desconhecida: «{key}».",
    "Rutas / pedidos por ciclo": "Rotas / pedidos por ciclo",
    "Planificar A-checks": "Programar A-checks"
}

# Resolve new Portuguese source labels back to legacy keys for English rendering.
PT_TO_ES = {value: key for key, value in PT_BR.items()}
