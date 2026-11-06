<div align="center">
  <h1>AM / 04 · TORRE DE CONTROLE</h1>
  <p><strong>Airline Manager 4 Bot / Flight Operations</strong></p>
  <p>Automação para o <a href="https://www.airlinemanager.com">Airline Manager 4</a> com painel desktop e web: decolagens, combustível, CO₂, manutenção, campanhas de marketing, rotas e compra de aeronaves.</p>
</div>

**Idioma padrão: Português (Brasil).** Inglês disponível como alternativa.

## Novo centro de operações

O painel web e o aplicativo desktop agora usam a identidade **AM/04 — Torre de Controle**: design técnico de alto contraste, telemetria com leitura rápida, console de eventos e comandos separados dos parâmetros. O painel web é responsivo e não depende de fontes, CSS ou serviços externos.

**[Conheça a arquitetura visual e os contratos da interface](docs/IDENTIDADE_VISUAL.md)**

As capturas históricas abaixo ainda mostram a interface anterior e serão atualizadas posteriormente em uma instalação real, sem dados fictícios de produção.

## Funcionalidades

- Decola aeronaves prontas e verifica os voos.
- Compra combustível e CO₂ usando histórico de preços, níveis mínimos e limites de saldo.
- Programa reparos e revisões A-check, e amplia vagas do hangar quando necessário.
- Avalia rotas, demanda, autonomia, assentos e melhorias das aeronaves.
- Planeja novas aquisições com estimativas de rentabilidade e metas de crescimento.
- Gerencia campanhas de reputação e ecológicas segundo o retorno estimado.
- Acompanha tarefas do jogo e coleta recompensas disponíveis.
- Exibe os dados da companhia, o histórico de operações e as configurações em painel desktop e web.
- Envia notificações pelo Telegram e tenta reiniciar após falhas.
- Oferece **Simulação (sem gastos)** para avaliar decisões antes de executá-las.

As estimativas adaptam-se aos modos Fácil e Realista e dependem das informações disponíveis da companhia.

<details>
<summary><b>Imagens do desktop e painel web</b></summary>

| Desktop | Painel web |
| --- | --- |
| <img src="screenshots/desktop-mercado.png" width="420" alt="Aba Mercado no desktop"> | <img src="screenshots/web-mercado.png" width="420" alt="Aba Mercado no navegador"> |
| <img src="screenshots/desktop-flota.png" width="420" alt="Aba Frota no desktop"> | <img src="screenshots/web-flota.png" width="420" alt="Aba Frota no navegador"> |
| <img src="screenshots/desktop-aviones.png" width="420" alt="Aba Aeronaves no desktop"> | <img src="screenshots/web-aviones.png" width="420" alt="Aba Aeronaves no navegador"> |
| <img src="screenshots/desktop-opciones.png" width="420" alt="Aba Opções no desktop"> | <img src="screenshots/web-opciones.png" width="420" alt="Aba Opções no navegador"> |
| <img src="screenshots/desktop-mercado-light.png" width="420" alt="Tema claro no desktop"> | <img src="screenshots/web-mercado-light.png" width="420" alt="Tema claro no navegador"> |
| | <img src="screenshots/web-mobile.png" width="200" alt="Painel web no celular"> |

As imagens são exemplos de uma versão anterior. Para atualizar as capturas, utilize o gerador da pasta scripts no ambiente compatível.
</details>

## Instalação fácil no Raspberry Pi OS e Ubuntu

Execute:

~~~bash
git clone https://github.com/andreypiekas/ArlineManager4BOTWEB.git
cd ArlineManager4BOTWEB
bash instalar.sh --rede-local
~~~

O instalador configura dependências, Chromium, Python, painel web e serviço systemd para inicialização automática. Use a opção **--configurar-login** para informar credenciais. Novos perfis começam em **modo simulação**.

**[Guia completo para Raspberry Pi OS e Ubuntu](docs/INSTALACAO_LINUX.md)**

## Instalação manual no Windows, Linux e macOS

Requisitos: Python 3.10 ou superior e Google Chrome ou Chromium compatível.

~~~bash
git clone https://github.com/andreypiekas/ArlineManager4BOTWEB.git
cd ArlineManager4BOTWEB
python -m venv .venv
~~~

Ative o ambiente virtual: no Windows use **.venv\Scripts\activate**; no Linux/macOS use **source .venv/bin/activate**. Depois execute:

~~~bash
pip install -r requirements.txt
python src/main.py
~~~

Informe o login do jogo, revise as opções e clique em **INICIAR BOT**. Para testar decisões sem gastos, ative **Simulação** antes de iniciar.

## Painel web e execução em segundo plano

Para executar sem a interface desktop:

~~~bash
python src/main.py --web
~~~

O painel fica disponível em **http://127.0.0.1:8744/** por padrão. Para acesso pela rede local, altere a opção de host do painel web e configure um token secreto de autenticação. Nunca exponha diretamente a porta web na internet.

Em instalações Linux, gerencie o serviço com:

~~~bash
sudo systemctl status am4bot@principal
sudo systemctl restart am4bot@principal
sudo journalctl -u am4bot@principal -f
~~~

## Perfis de diferentes companhias

Cada perfil usa credenciais, configurações, dados, sessão do navegador e porta web independentes. Use **--profile companhia2** para iniciar outro perfil. O perfil principal utiliza as pastas **config/** e **data/**; os demais ficam em **profiles/nome/**. Evite executar o mesmo perfil em dois computadores simultaneamente.

## Telegram

Crie um bot por meio do [@BotFather](https://t.me/BotFather), envie uma mensagem a ele e consulte a API **getUpdates** para obter o chat_id. Em **config/secrets.ini**, configure:

~~~ini
[telegram]
bot_token = SEU_TOKEN
chat_id = SEU_CHAT_ID
~~~

Para testar a integração, execute **python src/notify.py**. Mantenha o arquivo de segredos privado (chmod 600 no Linux).

## Guia detalhado das configurações

O bot verifica a companhia aérea periodicamente: lê o saldo, administra campanhas, repara aeronaves, ajusta assentos, decola voos disponíveis, compra combustível e CO₂, cria rotas, adquire aeronaves ou economiza para uma meta. As ações ficam registradas no painel e podem ser enviadas pelo Telegram.

Passe o mouse sobre uma configuração para abrir a ajuda contextual em português.

### Barra lateral

- **Perfis** — Cada perfil usa uma conta, configurações, dados e sessão do navegador independentes.
- **Conta** — Credenciais de acesso ao Airline Manager. Deixe em branco para fazer login manualmente no Chrome.
- **Lembrar credenciais** — Armazena as credenciais localmente em config/secrets.ini, que não é enviado ao Git.
- **Iniciar bot** — Abre o navegador e inicia os ciclos automáticos. Salve as configurações antes.
- **Parar bot** — Interrompe o bot após concluir a etapa atual e fecha o navegador.
- **Executar ciclo agora** — Executa imediatamente uma nova verificação, sem aguardar o intervalo.
- **Status** — Estado atual do bot, tempo para o próximo ciclo e informações de erro.
- **Aparência** — Escolha entre aparência clara, escura ou padrão do sistema.
- **Idioma** — Idioma da interface: português brasileiro ou inglês. A alteração do idioma do jogo depende das opções disponíveis nele.

### Indicadores

- **Dinheiro** — Saldo, renda líquida estimada por dia e pontos da companhia aérea.
- **Reputação** — Reputação e campanhas ativas, que influenciam a ocupação dos voos.
- **Combustível** — Estoque de combustível, preço por 1.000 libras e limite de compra.
- **CO₂** — Estoque de CO₂, preço por 1.000 cotas e limite de compra.
- **Frota** — Aeronaves em voo, estacionadas e pendentes de entrega ou manutenção.
- **Meta** — Progresso financeiro e prazo estimado para adquirir a aeronave desejada.

### Aba Mercado

- **Comprar combustível a ≤ $** — Compra combustível neste preço ou abaixo, mesmo que o histórico indique esperar.
- **Comprar CO₂ a ≤ $** — Compra CO₂ neste preço ou abaixo, mesmo que o histórico indique esperar.
- **Estoque mínimo (%)** — Abaixo deste nível, repõe os insumos mesmo que o preço esteja alto.
- **Estoque máximo (dias)** — Limita o estoque à previsão de consumo por dias. Zero permite encher completamente.
- **Gasto máximo (% do saldo)** — Percentual máximo do saldo disponível acima da reserva por compra.
- **Intervalo mínimo (min)** — Tempo mínimo entre verificações automáticas.
- **Intervalo máximo (min)** — Tempo máximo entre verificações; pousos e preços podem antecipar o ciclo.
- **Percentil de compra (%)** — Compra nos percentis de preços mais baixos dos últimos dias.
- **Percentil excepcional (%)** — Preço excepcional pode liberar compras maiores e repetidas na mesma meia hora. Zero desativa.
- **Histórico (dias)** — Quantidade de dias usada na análise do histórico de preços.
- **Máx. combustível por compra** — Quantidade máxima de combustível por compra. 9.999.999 libera o limite do tanque.
- **Máx. CO₂ por compra** — Quantidade máxima de CO₂ por compra. 9.999.999 libera o limite do tanque.
- **Compra inteligente com histórico de preços** — Compra segundo os preços mais vantajosos do histórico.

### Aba Frota

- **Reparar a partir de desgaste (%)** — Desgaste percentual a partir do qual deve reparar uma aeronave.
- **A-check quando restarem ≤ horas** — Horas restantes para iniciar a programação do A-check.
- **Reserva de caixa ($)** — Valor protegido contra compras não essenciais, preservando a operação.
- **Rota máxima para aeronave pequena (km)** — Distância máxima de rotas para aeronaves pequenas e médias.
- **Rota máxima para aeronave grande (km)** — Distância máxima de rotas para aeronaves de grande porte.
- **Pista mínima (pés)** — Comprimento mínimo da pista do aeroporto de destino.
- **Vagas disponíveis no hangar** — Quantidade de vagas que o bot tenta manter livres no hangar.
- **Rutas / pedidos por ciclo** — Limita novas rotas e pedidos de aeronaves por ciclo.
- **Oficina: retorno em até ≤ dias** — Prazo máximo para recuperar o custo de melhorias e perda de receita durante a parada.
- **Reparar aeronaves desgastadas** — Programa reparos das aeronaves que atingirem o desgaste definido.
- **Planificar A-checks** — Programa o A-check quando restarem poucas horas.
- **Criar rotas para aeronaves estacionadas** — Cria rotas com demanda adequada para aeronaves estacionadas.
- **Ampliar o hangar quando estiver cheio** — Compra expansão do hangar quando estiver perto do limite.
- **Assentos executiva / primeira conforme a demanda** — Distribui assentos entre econômica, executiva e primeira classe conforme a demanda.
- **Melhorias: velocidade, combustível e CO₂** — Avalia melhorias de velocidade, consumo de combustível e emissões de CO₂.

### Aba Aeronaves

- **Preço máximo sem meta (0 = livre)** — Limite de preço sem meta definida; zero remove o limite.
- **Comprar aeronaves** — Permite comprar aeronaves, desde que não haja outras estacionadas sem rota.
- **Economizar para uma aeronave desejada** — Economiza para comprar a aeronave desejada sem comprometer a reserva.
- **Investir em aeronaves menores se anteciparem a meta** — Compra aeronaves menores somente se ajudarem a atingir a meta mais cedo.
- **Aeronave desejada** — Escolha um modelo ou a progressão automática, que evolui conforme o lucro da companhia.
- **Modelo fixo sem meta** — Modelo fixo a comprar quando não houver uma meta de aquisição.

### Aba Opções

- **Campanha de reputação (1-4)** — Nível da campanha de reputação entre 1 e 4.
- **Duração da campanha (h)** — Duração das campanhas: 4, 8, 12, 16, 20 ou 24 horas.
- **Decolar aeronaves** — Decola as aeronaves disponíveis em cada ciclo.
- **Comprar combustível** — Compra combustível conforme os critérios da aba Mercado.
- **Comprar CO₂** — Compra CO₂ conforme os critérios da aba Mercado.
- **Campanhas de reputação** — Inicia campanhas de reputação se o retorno justificar o custo.
- **Campanha ecológica** — Mantém campanha ecológica enquanto for vantajosa e houver CO₂.
- **Monitorar a lista de tarefas do jogo** — Monitora tarefas e coleta recompensas disponíveis no jogo.
- **Iniciar o bot ao abrir** — Inicia automaticamente o bot ao abrir o aplicativo.
- **Manter a sessão do navegador** — Mantém os cookies e os dados da sessão do Chrome.
- **Navegador em segundo plano (headless)** — Executa o navegador oculto; CAPTCHAs ainda exigem intervenção manual.
- **Notificações pelo Telegram** — Envia eventos importantes e um resumo diário para o Telegram.
- **Telegram: avisar também as decolagens** — Envia também avisos a cada decolagem.
- **Reiniciar automaticamente após erro** — Reinicia automaticamente após falhas, com intervalo crescente.
- **Simulação (sem gastos)** — Simula ações sem executar compras ou mudanças no jogo.

### Registros e notificações

- **Registros** — O bot informa compras, partidas, rotas, manutenção, erros e tarefas executadas. O painel web e o aplicativo mostram os mesmos eventos.
- **Telegram** — Configure a seção `[telegram]` em `config/secrets.ini`. Os alertas de decolagem podem ser desativados para reduzir notificações.
- **Modo simulação** — Ative para verificar as decisões sem fazer compras nem modificar a companhia aérea.

### Painel web e operação contínua

Execute `python src/main.py --web` para iniciar somente o painel web. O endereço padrão é `http://127.0.0.1:8744/`. Para acesso pela rede local, utilize token de autenticação. Os scripts da pasta `scripts/` ajudam na execução no Windows e no Raspberry Pi.

### Segurança e compatibilidade

Mantenha `config/secrets.ini` privado e não faça commit de credenciais. O idioma do aplicativo é português brasileiro por padrão, com inglês opcional. O bot somente seleciona português dentro do jogo se esse idioma existir nas opções da conta; caso contrário, preserva o idioma atual do jogo.



## Arquivos de configuração

- **config/defaults.ini**: configurações padrão e seletores de elementos do jogo, versionados no Git.
- **config/settings.ini**: configurações específicas do perfil principal; ignorado pelo Git.
- **config/secrets.ini**: credenciais do jogo, token do painel web e Telegram; mantenha privado.
- **profiles/nome/**: configuração e dados dos perfis adicionais.
- **data/prices.json**: histórico de preços; **data/market.json**: mercado de aeronaves; **data/state.json**: estado e contadores do bot.
- **data/logs/am4bot.log**: registro de execução.

As seções de configuração são **[settings]** (valores numéricos), **[options]** (botões de ativação), **[web]** (rede e porta), **[app]** (aparência e idioma pt_BR ou en) e **[selectors]** (seletores do jogo, definidos apenas no arquivo de padrões).

## Observações

- O jogo pode modificar a estrutura das páginas; a automação Selenium depende desses elementos.
- Se surgir CAPTCHA, faça a verificação manualmente; o bot não contorna mecanismos de segurança.
- As estimativas de lucro não garantem resultados.
- A automação pode ser restrita pelos termos do jogo; confira as regras antes de utilizá-la.
- O projeto usa a licença MIT. O aviso de copyright obrigatório está preservado no arquivo [LICENSE](LICENSE).
