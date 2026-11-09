"""Contextual help in Brazilian Portuguese (default) and English."""

HELP: dict[str, str] = {
    "language": "Idioma da interface: português brasileiro ou inglês. A alteração do idioma do jogo depende das opções disponíveis nele.",
    "profile": "Cada perfil usa uma conta, configurações, dados e sessão do navegador independentes.",
    "game_mode": "O bot identifica se a conta está no modo fácil ou realista e ajusta suas estimativas.",
    "account": "Credenciais de acesso ao Airline Manager. Deixe em branco para fazer login manualmente no Chrome.",
    "remember": "Armazena as credenciais localmente em config/secrets.ini, que não é enviado ao Git.",
    "btn_start": "Abre o navegador e inicia os ciclos automáticos. Salve as configurações antes.",
    "btn_stop": "Interrompe o bot após concluir a etapa atual e fecha o navegador.",
    "btn_run_now": "Executa imediatamente uma nova verificação, sem aguardar o intervalo.",
    "status": "Estado atual do bot, tempo para o próximo ciclo e informações de erro.",
    "theme": "Escolha entre aparência clara, escura ou padrão do sistema.",
    "money": "Saldo, renda líquida estimada por dia e pontos da companhia aérea.",
    "fuel": "Estoque de combustível, preço por 1.000 libras e limite de compra.",
    "co2": "Estoque de CO₂, preço por 1.000 cotas e limite de compra.",
    "fleet": "Aeronaves em voo, estacionadas e pendentes de entrega ou manutenção.",
    "reputation": "Reputação e campanhas ativas, que influenciam a ocupação dos voos.",
    "goal": "Progresso financeiro e prazo estimado para adquirir a aeronave desejada.",
    "fuel_price_good": "Compra combustível neste preço ou abaixo, mesmo que o histórico indique esperar.",
    "co2_price_good": "Compra CO₂ neste preço ou abaixo, mesmo que o histórico indique esperar.",
    "buy_percentile": "Compra nos percentis de preços mais baixos dos últimos dias.",
    "excellent_percentile": "Preço excepcional pode liberar compras maiores e repetidas na mesma meia hora. Zero desativa.",
    "history_days": "Quantidade de dias usada na análise do histórico de preços.",
    "min_stock_pct": "Abaixo deste nível, repõe os insumos mesmo que o preço esteja alto.",
    "stock_days": "Limita o estoque à previsão de consumo por dias. Zero permite encher completamente.",
    "market_max_spend_pct": "Percentual máximo do saldo disponível acima da reserva por compra.",
    "fuel_quantity_buy": "Quantidade máxima de combustível por compra. 9.999.999 libera o limite do tanque.",
    "co2_quantity_buy": "Quantidade máxima de CO₂ por compra. 9.999.999 libera o limite do tanque.",
    "cycle_min_minutes": "Tempo mínimo entre verificações automáticas.",
    "cycle_max_minutes": "Tempo máximo entre verificações; pousos e preços podem antecipar o ciclo.",
    "smart_buy": "Compra segundo os preços mais vantajosos do histórico.",
    "auto_repair": "Programa reparos das aeronaves que atingirem o desgaste definido.",
    "auto_check": "Programa o A-check quando restarem poucas horas.",
    "auto_route": "Cria rotas com demanda adequada para aeronaves estacionadas.",
    "analyze_duplicate_routes": "Continua calculando alternativas para rotas duplicadas mesmo se a criação automática de novas rotas estiver desligada. Apenas gera propostas, sem executar trocas reais.",
    "route_min_profit_gain_pct": "Melhoria mínima percentual do lucro diário estimado ao sugerir trocar uma rota com lucro atual conhecido (padrão 5%). Estimativas não garantem resultado.",
    "route_analysis_per_cycle": "Quantidade de aeronaves duplicadas avaliadas a cada ciclo, independente das compras e novas rotas. Padrão 5, máximo 20.",
    "allow_duplicate_routes": "Desativado: bloqueia novas rotas duplicadas nos dois sentidos e planeja mudar aeronaves repetidas para destinos lucrativos quando elas estiverem confirmadamente na base. Ativado: permite duplicidades.",
    "auto_hangar": "Compra expansão do hangar quando estiver perto do limite.",
    "repair_wear_pct": "Desgaste percentual a partir do qual deve reparar uma aeronave.",
    "check_hours_min": "Horas restantes para iniciar a programação do A-check.",
    "cash_reserve": "Valor protegido contra compras não essenciais, preservando a operação.",
    "route_max_distance": "Distância máxima de rotas para aeronaves pequenas e médias.",
    "route_max_distance_big": "Distância máxima de rotas para aeronaves de grande porte.",
    "route_min_runway": "Comprimento mínimo da pista do aeroporto de destino.",
    "hangar_min_free": "Quantidade de vagas que o bot tenta manter livres no hangar.",
    "fleet_actions_per_cycle": "Limita novas rotas e pedidos de aeronaves por ciclo.",
    "auto_seats": "Distribui assentos entre econômica, executiva e primeira classe conforme a demanda.",
    "seats_max_payback": "Prazo máximo para recuperar o custo de melhorias e perda de receita durante a parada.",
    "auto_mods": "Avalia melhorias de velocidade, consumo de combustível e emissões de CO₂.",
    "autobuy_aircraft": "Permite comprar aeronaves, desde que não haja outras estacionadas sem rota.",
    "save_for_goal": "Ative para usar Progressão automática ou Modelo específico da meta de compra. Se desativada, o bot usa o Modelo fixo sem meta, ou escolhe a opção mais rentável.",
    "goal_model": "Escolha Progressão automática para o bot selecionar aeronaves por rentabilidade, ou Modelo específico para economizar e comprar a aeronave escolhida do mercado. Requer a opção Economizar para uma aeronave desejada ativa.",
    "goal_invest": "Ativada: o bot pode comprar outras aeronaves rentáveis enquanto economiza para a escolhida. Desative para comprar somente o modelo definido na meta.",
    "aircraft_model": "Modelo fixo usado somente quando Economizar para uma aeronave desejada estiver desativado. Deixe vazio para comprar a aeronave mais rentável.",
    "engine_preference": "Padrão do jogo mantém o comportamento anterior. Escolha motor específico, mais rápido ou mais econômico para validar a motorização antes de comprar. Se não for possível confirmar a seleção, a compra será bloqueada.",
    "aircraft_max_price": "Limite de preço sem meta definida; zero remove o limite.",
    "auto_depart": "Decola as aeronaves disponíveis em cada ciclo, independentemente da opção Criar rotas para aeronaves estacionadas.",
    "block_duplicate_departures": "DESATIVADO (padrão): as rotas já existentes podem decolar, mesmo repetidas; proibir novas rotas duplicadas continua funcionando. ATIVADO: bloqueia Decolar todas quando houver duplicidades conhecidas e tenta despacho individual seguro, se habilitado.",
    "selective_depart": "Com duplicidades proibidas, tenta decolar somente aeronaves aprovadas e com um controle individual explícito no jogo. Nunca envia Decolar todas nessa situação; se o jogo não oferecer esse comando, não decola nenhuma por segurança.",
    "experimental_id_batch_depart": "RISCO: força uma única decolagem por ciclo via route_depart.php?mode=all&ids=<ID aprovado>. Outros bots usam este parâmetro, mas NÃO comprovamos se o jogo respeita a seleção. Pode decolar outras aeronaves. Desligado por padrão; use apenas se aceitar esse risco.",
    "autobuy_fuel": "Compra combustível conforme os critérios da aba Mercado.",
    "autobuy_co2": "Compra CO₂ conforme os critérios da aba Mercado.",
    "auto_marketing": "Inicia campanhas de reputação se o retorno justificar o custo.",
    "marketing_eco": "Mantém campanha ecológica enquanto for vantajosa e houver CO₂.",
    "auto_checklist": "Monitora tarefas e coleta recompensas disponíveis no jogo.",
    "marketing_campaign": "Nível da campanha de reputação entre 1 e 4.",
    "marketing_hours": "Duração das campanhas: 4, 8, 12, 16, 20 ou 24 horas.",
    "start_on_launch": "Inicia automaticamente o bot ao abrir o aplicativo.",
    "keep_session": "Mantém os cookies e os dados da sessão do Chrome.",
    "headless": "Executa o navegador oculto; CAPTCHAs ainda exigem intervenção manual.",
    "telegram": "Ativa ou desativa todos os envios para o Telegram. As preferências abaixo continuam salvas.",
    "telegram_errors": "Alertas de erros e interrupções inesperadas do bot. Recomenda-se manter ativo.",
    "telegram_status": "Mensagens de início e parada voluntária do bot.",
    "telegram_daily": "Resumo diário com saldo, estoque, frota e atividades, no horário configurado.",
    "telegram_departures": "Notificações de decolagens executadas pelo bot.",
    "telegram_fuel": "Confirmações de compras de combustível.",
    "telegram_co2": "Confirmações de compras de créditos de CO₂.",
    "telegram_routes": "Rotas criadas e confirmadas.",
    "telegram_aircraft": "Pedidos de novas aeronaves confirmados.",
    "telegram_maintenance": "Reparos e A-checks programados.",
    "telegram_hangar": "Novas vagas de hangar adquiridas.",
    "telegram_workshop": "Mudanças de assentos e melhorias na oficina.",
    "telegram_marketing": "Contratação de campanhas de reputação ou ecológicas.",
    "telegram_checklist": "Atividades e recompensas da lista de tarefas do jogo.",
    "telegram_simulation": "Mensagens de ações que seriam executadas em modo simulação.",
    "auto_restart": "Reinicia automaticamente após falhas, com intervalo crescente.",
    "dry_run": "Simula ações sem executar compras ou mudanças no jogo.",
    "summary_hour": "Horário de envio do resumo diário pelo Telegram.",
    "cash_sync_seconds": "A cada 30 a 600 segundos, durante a espera entre ciclos, o bot recarrega a página do jogo e lê o saldo real. Reflete compras e alterações feitas pelo celular sem aguardar o ciclo completo. O navegador é acessado apenas pela thread do bot.",
    "telegram_test": "Testa o envio para o chat configurado.",
    "save": "Salva os valores desta aba; as opções são salvas imediatamente.",
    "open_log": "Abre o arquivo de registro completo da operação.",
    "clear_log": "Limpa o painel de registros sem alterar o arquivo."
}

HELP_EN = {
    # ---- sidebar
    "language": "Language of the window and the web dashboard. It also switches your game account to that language at "
                "the next check (the bot works with the game in any language). The bot reports messages in Brazilian Portuguese.",
    "profile": "Each profile is one airline (one game account) with its own settings, credentials, Chrome session, data "
               "and web dashboard. Pick another one to open it in another window (they can run at the same time) or "
               "create a new one: it copies your current settings and puts a shortcut on the desktop.",
    "game_mode": "Mode of the game account, read at every check. In realism flights go at the aircraft's speed and "
                 "tickets are cheaper than in easy mode (x1.5); the bot adapts its profit, route and seat calculations.",
    "account": "Your Airline Manager e-mail and password. With “Remember credentials” they are saved in "
               "config/secrets.ini, which is never uploaded to git. Leave them empty to log in by hand in Chrome.",
    "remember": "Saves the e-mail and password in config/secrets.ini so you do not type them every time. "
                "Unticking it deletes that file.",
    "btn_start": "Opens Chrome, logs in and keeps checking the airline in a loop. Saves the settings before starting.",
    "btn_stop": "Stops the bot when the current step ends and closes Chrome.",
    "btn_run_now": "Skips the wait and runs a full check right now.",
    "status": "State of the bot and countdown to the next check. After an error you see the reason and the countdown "
              "of the automatic restart.",
    "theme": "Light, dark or the system theme.",
    # ---- statistic tiles
    "money": "Money of the airline. Below, the estimated net income per day while the bot runs (fuel and CO2 count "
             "when burnt, not when bought) and the game points (the bot does not spend them).",
    "fuel": "How full the fuel tank is. Below, the current price per 1,000 lbs and the price under which it buys now.",
    "co2": "How full the CO2 tank is. Below, the current price of 1,000 quotas and the current buy threshold.",
    "fleet": "Aircraft in the fleet. Below: flying, parked without a route and pending (delivery or in the workshop "
             "changing seats).",
    "reputation": "Airline reputation, including running campaigns. Aircraft fly about this full. Below, the time left "
                  "on the first campaign to end.",
    "goal": "Progress towards the goal aircraft: money saved above the reserve and estimated arrival at your income rate.",
    # ---- market
    "fuel_price_good": "Below this price it always buys fuel, whatever the history says. "
                       "In brackets, the lowest price the bot has seen.",
    "co2_price_good": "Below this price it always buys CO2, whatever the history says. "
                      "In brackets, the lowest price the bot has seen.",
    "buy_percentile": "With smart buying, it buys when the price is within the cheapest X % of the last days. "
                      "25 = the cheapest quarter. Lower buys less often but cheaper.",
    "excellent_percentile": "Exceptional price: within the cheapest X % and also below your fixed good price, it fills the "
                            "tank with all the money above the reserve and may buy again in the same half hour. 0 turns it off.",
    "history_days": "How many days of prices are used for the percentiles.",
    "min_stock_pct": "If the tank drops below this percentage it tops up to that level at any price, so no aircraft "
                     "stays on the ground.",
    "stock_days": "It buys at most this many days of fuel or CO2 use (measured by the bot); twice that at an exceptional "
                  "price. That way money goes to new aircraft instead of sitting in the tank for weeks. 0 = fills the tank.",
    "market_max_spend_pct": "Largest share of the available money (above the reserve) spent on a normal fuel or CO2 purchase.",
    "fuel_quantity_buy": "Maximum fuel per purchase. With 9,999,999 it fills whatever fits.",
    "co2_quantity_buy": "Maximum CO2 per purchase. With 9,999,999 it fills whatever fits.",
    "cycle_min_minutes": "Minimum wait between checks. The bot picks a random time between the minimum and the maximum.",
    "cycle_max_minutes": "Maximum wait between checks. It comes back earlier when an aircraft is about to land or the "
                         "price is about to change.",
    "smart_buy": "Uses the price history to decide: buys when the price is in the low part of the last days, not only "
                 "below the fixed price.",
    # ---- fleet
    "auto_repair": "Plans the repair of aircraft whose wear passes the threshold.",
    "auto_check": "Plans the A-check when an aircraft has few hours left.",
    "auto_route": "Gives parked aircraft a route: the busiest route the aircraft can fly, with the game's autoprice.",
    "analyze_duplicate_routes": "Computes profitable alternatives for duplicate routes even when automatic new-route creation is off. Proposals only; no live rerouting.",
    "route_min_profit_gain_pct": "Minimum percentage improvement over known estimated current profit before proposing a replacement (default 5%). Estimates are not guaranteed.",
    "route_analysis_per_cycle": "Number of duplicate-route aircraft analyzed in each cycle; separate from live purchase and routing quota. Default 5, maximum 20.",
    "auto_hangar": "When few hangar slots are left it buys one more (about $25,000) so another aircraft can always be bought.",
    "repair_wear_pct": "Wear from which an aircraft is repaired.",
    "check_hours_min": "The A-check is planned when this many hours or fewer are left.",
    "cash_reserve": "Cushion for the essentials: below this amount it only pays repairs, A-checks, fuel or CO2 for a "
                    "nearly empty tank and the route of an aircraft already bought. No aircraft, campaigns, workshop, "
                    "hangar or normal fuel purchases.",
    "route_max_distance": "Maximum distance when searching routes for small and medium aircraft.",
    "route_max_distance_big": "Maximum distance when searching routes for aircraft of 150 seats or more. Long routes "
                              "pay more expensive tickets.",
    "route_min_runway": "Minimum runway of the destination airport when searching routes.",
    "hangar_min_free": "Free hangar slots it tries to keep when “Expand the hangar” is on.",
    "fleet_actions_per_cycle": "Maximum new routes and aircraft orders per check, so it does not spend everything at once.",
    "auto_seats": "When an aircraft is at the base, it reads the demand of its route and gives it first and business "
                  "seats up to that demand; the rest economy. Per slot, first pays more than business and business more "
                  "than economy. It only changes when it pays (see “pay back in”).",
    "seats_max_payback": "It only changes the seats or installs an upgrade if its cost, plus what the aircraft does not earn "
                         "in the workshop, comes back in this many days or fewer.",
    "auto_mods": "When an aircraft is at the base, it works out what each upgrade of the game workshop would earn: "
                 "speed +10 % (more flights a day), fuel -10 % and CO2 -10 %. It only installs those that pay back within "
                 "“pay back in”. They are permanent and each keeps the aircraft about 13 minutes in the workshop.",
    # ---- aircraft and goal
    "autobuy_aircraft": "Lets the bot buy aircraft. It never buys while aircraft are parked without a route.",
    "save_for_goal": "Savings mode: puts money aside for the goal aircraft and buys it as soon as it can, without "
                     "touching the reserve.",
    "goal_model": "The aircraft you want. “Automatic (ladder)” picks the next step by itself: the aircraft that earns "
                  "most per day among those costing at most one day of income and paying back in 5 days or fewer. As "
                  "income grows, the ladder climbs to bigger aircraft. You can also pick a fixed model.",
    "goal_invest": "While saving, it buys a smaller aircraft only if it pays back in less than half the time left to "
                   "the goal: that way the goal comes sooner. Off, it only saves.",
    "aircraft_model": "Without a goal: always buys this model instead of the most profitable one.",
    "aircraft_max_price": "Without a goal: never buys aircraft more expensive than this. 0 = no limit.",
    # ---- options
    "auto_depart": "Departs ready aircraft each cycle, independently of automatic route creation.",
    "block_duplicate_departures": "OFF (default): existing aircraft depart even if their routes are duplicated; creation policy is separate. ON: blocks Depart All on known duplicate routes and attempts safe selective dispatch if enabled.",
    "selective_depart": "When duplicate routes are prohibited, searches for native per-aircraft departure controls and only dispatches independently approved flights. Never uses the bulk button if a duplicate is known; if the game offers only Depart All, it pauses without sending unverified requests.",
    "experimental_id_batch_depart": "RISK: attempts one approved aircraft per cycle using route_depart.php?mode=all&ids=<ID>. Other bots use this parameter but the game backend may IGNORE the filter and depart other planes. OFF by default; enable only after accepting this risk.",
    "autobuy_fuel": "Buys fuel with the rules of the Market tab.",
    "autobuy_co2": "Buys CO2 with the rules of the Market tab.",
    "auto_marketing": "Keeps a reputation campaign running: aircraft fly as full as the reputation, so every departure "
                      "earns more. It only launches it when the extra tickets (from your measured income) beat its "
                      "price, and never goes below the cash reserve.",
    "marketing_eco": "Keeps the eco-friendly campaign running (12 h, +10 % reputation, cheap) as long as it pays. It "
                     "only works while you hold CO2 quotas.",
    "auto_checklist": "Reads the game checklist (bottom left), reports finished tasks and collects rewards when the game "
                      "offers a button.",
    "marketing_campaign": "Which reputation campaign it launches: 1 (+5-10 %, the cheapest) to 4 (+25-35 %). Number 4 "
                          "gives the most reputation per dollar.",
    "marketing_hours": "Length of each reputation campaign: 4, 8, 12, 16, 20 or 24 h. Long ones are a bit cheaper per "
                       "hour but keep running if you stop the bot.",
    "start_on_launch": "Starts the bot as soon as the app opens. Handy with the shortcut in the Windows startup folder.",
    "keep_session": "Keeps the Chrome profile in the profile folder. The game asks for the login anyway, but cookies and "
                    "settings stay.",
    "headless": "Chrome without a window. More discreet; if the game shows a captcha you will not see it.",
    "telegram": "Master switch for every Telegram notification; individual preferences are preserved.",
    "telegram_errors": "Errors and unexpected bot interruptions. Recommended to leave enabled.",
    "telegram_status": "Bot startup and normal shutdown.",
    "telegram_daily": "Daily balance, stock, fleet and activity summary at your selected hour.",
    "telegram_departures": "Alerts when aircraft are dispatched.",
    "telegram_fuel": "Confirmed fuel purchases.",
    "telegram_co2": "Confirmed CO2 purchases.",
    "telegram_routes": "New routes created.",
    "telegram_aircraft": "New aircraft orders.",
    "telegram_maintenance": "Repairs and A-checks scheduled.",
    "telegram_hangar": "New hangar slots purchased.",
    "telegram_workshop": "Seat configuration and workshop upgrades.",
    "telegram_marketing": "Marketing campaigns started.",
    "telegram_checklist": "Game checklist tasks and rewards.",
    "telegram_simulation": "Proposed actions during dry-run mode.",
    "auto_restart": "If the bot stops because of an error, it starts again by itself after 2 minutes (then 4, 8... up to 30).",
    "dry_run": "Dry run: the bot does everything the same but buys and plans nothing; it only writes what it would do.",
    "summary_hour": "Hour from which the daily Telegram summary is sent.",
    "cash_sync_seconds": "Every 30 to 600 seconds between runs, refresh the game page and read the real balance, including changes made on mobile. Never opens Selenium from the web thread.",
    "telegram_test": "Sends a test message to check the token and chat id of config/secrets.ini.",
    # ---- panels
    "save": "Saves the numbers of this tab. Switches are saved as soon as you change them.",
    "open_log": "Opens data/logs/am4bot.log with all the detail, including what is not shown here.",
    "clear_log": "Empties the panel. The log file is not touched.",
}
