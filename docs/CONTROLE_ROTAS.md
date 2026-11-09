# Controle de rotas e aeronaves (AM/04)

## Objetivo

O bot mantém um cadastro por perfil da relação entre cada aeronave, sua matrícula,
modelo, origem e destino, com histórico de mudanças e lucro diário estimado.
`DUB → GRU` e `GRU → DUB` são **a mesma rota** para o controle.

Arquivo local: `data/routes_registry.json` (no perfil principal) ou
`profiles/<nome>/data/routes_registry.json` (nos demais perfis).
Gravação atômica; as consultas do painel são independentes do WebDriver.

## Interface

Abra **Rotas e aeronaves** no menu lateral do painel web. A tela apresenta:

- Todas as aeronaves **já identificadas** pelo controle, incluindo as vistas em
  páginas anteriores; matrícula/ID, modelo, origem, destino e última leitura.
- Lucro estimado por dia, quando houver dados de mercado suficientes.
- Duplicidades em qualquer sentido, propostas de nova rota e situação operacional.
- Histórico de vinculações e mudanças, inclusive intervenções manuais.
- Formulário para corrigir aeroportos de uma aeronave que não foi identificada
  automaticamente. Esta correção modifica apenas o **relatório**, nunca o jogo.

A API autenticada é `GET /api/routes`. A gravação manual requer
`POST /api/routes`, cabeçalho `X-AM4: 1`, autenticação já existente no painel
e objeto `{"action":"register","aircraft_id":"123","registration":"XP-123","origin_code":"DUB","destination_code":"GRU"}`.

## Política de duplicidade

Em **Parâmetros → Frota**, configure **Permitir aeronaves na mesma rota
(ida/volta)**:

- **Desativado (padrão):** o bot rejeita novas atribuições repetidas, inclusive
  com origem/destino invertidos. Para duplicidades existentes no cadastro,
  calcula alternativas por lucro líquido diário aproximado e prepara
  redirecionamentos quando a opção **Criar rotas para aeronaves estacionadas**
  também estiver ativa.
- **Ativado:** permite múltiplas aeronaves no mesmo par de aeroportos.
  Desativa o processo de correção automática de duplicidades.

Entre os aviões que dividem a rota, o controle prefere preservar aquele com
maior lucro estimado (ou o registro mais antigo quando não houver comparação)
e propõe novas rotas para os demais.

## Execução protegida

O controle acumula um relatório histórico de aeronaves e rotas, busca
alternativas com lucro estimado e registra propostas sem alterar o jogo.
Uma aeronave com dados insuficientes apresenta a causa específica:
`aeronave_fora_da_base`, `localizacao_nao_confirmada`,
`rota_nao_confirmada_no_jogo`, `aeroportos_nao_confirmados`
ou `comprovacao_desatualizada`.

A mensagem da manutenção distingue agora aeronaves **na base** e
**fora da base/em voo**. Ter lido a localização de uma aeronave não
significa que ela esteja numa base. Encontrar DAC/OSL no seletor de
bases da companhia também não comprova a base específica daquele avião.

### Alterações de rotas existentes

**O redirecionamento real de uma aeronave que já possui rota está
temporariamente desabilitado.** O formulário `new_route_info.php` é
o fluxo de **criação de uma nova rota**, e ainda não foi comprovado
que ele substitui com segurança a rota de uma aeronave já atribuída.
O bot continuará calculando, simulando e registrando propostas, inclusive
fora do modo simulação, mas marcará `troca_de_rota_ainda_nao_validada`
em vez de enviar ordens de compra de nova rota.

### Deixar de criar rotas não interrompe as decolagens

As políticas **não são a mesma configuração**:

- **Criar rotas para aeronaves estacionadas** (`auto_route`): ativa ou
  desativa exclusivamente a criação automática de novas rotas.
- **Permitir aeronaves na mesma rota** (`allow_duplicate_routes`):
  permite ou proíbe **novas atribuições duplicadas**; o otimizador ainda
  pode sinalizar duplicidades existentes.
- **Decolar aeronaves** (`auto_depart`): habilita o despacho operacional.
- **Bloquear decolagens com rotas duplicadas**
  (`block_duplicate_departures`): **DESATIVADA por padrão**. Se ativada
  explicitamente, bloqueia `Decolar todas` quando existem duplicidades
  no registro histórico e tenta o despacho seletivo, se habilitado.

Por padrão, **rotas automáticas desligadas + proibição de criar rotas
duplicadas + decolagens ativadas** mantém o botão geral de decolagem
funcionando para rotas já cadastradas. Essa decisão **também pode
despachar aeronaves que compartilham rotas**: a política de criação de
novas rotas não impõe uma restrição operacional às existentes.

Quem deseja **proibir a decolagem de rotas repetidas** pode ativar
`block_duplicate_departures` na aba Opções. O bot então tentará
**Despacho individual seguro**, lendo a lista de aeronaves prontas
e aceitando só controles individuais nativos e identificados. Se o
jogo não expuser comandos individuais, nenhuma decolagem é enviada;
o endpoint por IDs é experimental e fica desligado por padrão.

O relatório é parcial e acumula aeronaves de páginas anteriores; a
ausência de duplicidades não comprova que toda a frota foi auditada.

A funcionalidade de criar rotas para aeronaves **sem rota** continua
independente e exige confirmações do próprio jogo, incluindo simulação,
custo e validação do formulário de criação.

O modo **Simulação (sem gastos)** calcula e registra propostas, sem enviar
pedidos de compra ou decolagem.


### Pré-validação de troca de rota

O módulo `src/reroute_preflight.py` consulta, somente para leitura,
`fleet_details.php?id=<ID da aeronave>`. Ele recupera o identificador
da rota a partir do controle nativo `fleet_ground.php?id=<ID da rota>`
e compara os aeroportos exibidos nos detalhes com a relação acumulada
no histórico (inclusive no sentido oposto).

O resultado fica junto à proposta de redirecionamento:
`preflight.route_id`, `preflight.status` e `preflight.endpoints`.
IDs ausentes, múltiplos IDs, aeronave em voo e aeroportos divergentes
**bloqueiam** a pré-validação. Esta consulta nunca envia uma ação de
aterramento, criação ou modificação de rota.

A substituição real permanece desativada enquanto o fluxo completo de
aterramento, criação e rollback não for testado no jogo autenticado.

## Limites conhecidos

O jogo pode mostrar somente parte da frota por página. O controle acumula as
relações vistas em diferentes ciclos, mas **não afirma possuir a lista
completa**. A ausência de uma aeronave em uma página não significa que ela foi
vendida ou mudou de rota. A lista "estacionadas sem rota", por outro lado,
é prova suficiente para limpar uma associação antiga naquele avião.

Nem toda versão do HTML do jogo apresenta os atributos da origem, destino ou
localização exata da aeronave usados na verificação. Nestes casos os registros
ficam como **rota não identificada** ou **aguardando confirmação no jogo**.
O fluxo do Selenium autenticado deve ser validado no seu servidor antes de
liberar redirecionamentos reais. Isso impede alterações arriscadas em contas
com várias bases, aeronaves em trânsito ou manutenção.

O otimizador baseia-se nos modelos e premissas de `src/route_optimizer.py`,
que utilizam referências de
[abc8747/am4](https://github.com/abc8747/am4) (MIT, Abraham Cheung). Lucro,
consumo, demanda e custo são estimativas, não valores garantidos pelo jogo.

## Validação

```bash
python -m pytest -q tests/test_route_registry.py tests/test_route_optimizer.py
```

Para inspecionar o relatório em execução, use a aba **Rotas e aeronaves**
no painel web. Não habilite execução de compras/alterações reais antes de
validar os registros da frota com **Simulação (sem gastos)**.

## Catálogo offline de aeroportos

A pesquisa do jogo lista bases pelo nome e ID (ex.: `2926: Chapecó, Brazil`) e frequentemente não apresenta IATA/ICAO. O bot usa `assets/airports_am4_codes.csv` para associar IDs a códigos, sem acessar rede durante o ciclo. Referência factual: https://github.com/eaingaran/airline-manager4/blob/master/airports.json; informações técnicas também presentes em https://github.com/abc8747/am4.

O catálogo é auxiliar e pode ficar desatualizado. IDs são confirmados pelo jogo antes de qualquer ação. DAC (3499), OSL (645), LAX (1440) e PBM (3146) podem ser extremos de rotas sem serem bases próprias. Se ambos faltam na lista de bases do jogador, o status correto é `rota_fora_das_bases`. O bot não inventa uma origem operacional nem autoriza troca de rota somente com o catálogo. A manutenção confirma se uma aeronave está numa base, mas não identifica qual é essa base.

## Diagnóstico do despacho em cada ciclo

A auditoria de rotas não é sinônimo de decolagem. Os logs de
`Controle de rotas` indicam apenas leitura da malha e estados de
manutenção; não provam que alguma aeronave foi despachada.

O bot registra agora `Diagnóstico de decolagem` em cada ciclo,
inclusive com `auto_depart` desativado, e informa:

- se a decolagem automática está ativa;
- se a simulação está ativa;
- se duplicidades estão permitidas e quantas são conhecidas;
- se escolheu despacho geral, seletivo ou bloqueio;
- se o botão geral estava disponível e se foi acionado.

O comando geral enviado é registrado como
`comando_geral_enviado_sem_confirmacao_individual`: **não** equivale
a dizer que todos os aviões decolaram. O painel **Rotas e aeronaves**
exibe o modo, o último horário de avaliação e o estado registrado.

Consulta sugerida:

```bash
sudo journalctl -u am4bot@principal --since "30 min ago" --no-pager | grep -Ei 'Diagnóstico de decolagem|Despacho individual|Decolagem geral|Erro inesperado ao decolar|Controle de rotas'
```

Se nenhuma linha de diagnóstico de decolagem aparecer após atualizar
`main` e reiniciar o serviço, verifique se o processo correto está
executando a versão nova do código e examine os logs sem filtro.


## Despacho por IDs (experimental — desativado)

O jogo exibe o comando nativo
`route_depart.php?mode=all&ids=x`, mas não apresentou botões individuais
na página de status. Projetos comunitários de AM4 chamam
`route_depart.php?mode=all&ids=<ids separados por vírgula>`:

- https://github.com/nem-web/am4-bot/blob/main/script.js
- https://github.com/nem-web/am4-bot/blob/main/testing.js

**A existência desse exemplo não prova que o servidor respeite uma lista
específica de IDs. O endpoint pode ignorar o filtro e despachar mais aviões.**

A opção **EXPERIMENTAL: decolagem por ID (API não verificada)** é
**desativada por padrão**. O bot continua operando com o algoritmo
de despacho individual comprovado pelo DOM enquanto esta opção estiver
desativada. Se o usuário optar por habilitar o experimento, o bot:

1. Audita a lista real das aeronaves prontas no jogo e o histórico de rotas;
2. Escolhe somente um avião aprovado, com leitura de rota recente;
3. Confirma que a página contém o comando nativo e o alvo continua pronto;
4. Em simulação, registra o ID selecionado e **não envia nenhum pedido**;
5. Fora de simulação, grava um bloqueio **persistente e de uso único**
   antes de tentar a chamada com `ids=<ID exato>`;
6. Verifica se a aeronave mudou de `#landedList` para `#inflightList` e
   se outra aeronave mudou inesperadamente.

Mesmo que a chamada seja bem-sucedida, **o experimento não se repete em
ciclos posteriores nem após reiniciar o serviço**. A chave
`experimental_departure_pilot` fica registrada por perfil em
`routes_registry.json`, para impedir repetição após resposta incerta ou
falha de comunicação. Não edite o registro para burlar o bloqueio sem
investigar o resultado.

Após uma tentativa, examine os registros de `Despacho experimental` e
compare a lista real de voos do jogo. Somente quando a seleção for
comprovada no jogo real é adequado avaliar a liberação de execução
seletiva contínua. A configuração não deve ser usada para contornar
limitações ou regras do serviço.


## Motor de planejamento de rotas — evolução de 08/11/2026

A criação automática de rotas e a análise de rotas repetidas passam a ser
duas operações **independentes**:

- `auto_route`: efetivamente cria novas rotas para aeronaves sem rota,
  condicionado a orçamento, permissões, alcance, pista e formulário real.
- `analyze_duplicate_routes`: **ligada por padrão**, mesmo com `auto_route`
  desligada. Analisa rotas repetidas, pesquisa destinos e grava propostas,
  porém **nunca altera uma rota existente** sem o fluxo de substituição
  validado em uma sessão autenticada.
- `route_min_profit_gain_pct`: percentual mínimo de aumento estimado
  do lucro diário ao comparar uma alternativa com um lucro atual estimado
  e disponível. Padrão **5%**. Quando não existe estimativa atual confiável,
  exige apenas lucro estimado positivo e identifica a comparação como
  indisponível; não inventa ganho líquido.

### Pesquisa e seleção

A estimativa considera demanda Y/J/F, alcance, velocidade, combustível,
CO₂, fator de ocupação e modo de jogo. O cálculo tem limitações (custos,
índices e parâmetros não expostos no jogo) e serve para priorização.

- Quando o mercado fornece dados suficientes para calcular lucro, **rotas
  conhecidamente deficitárias ou com lucro zero não são criadas**.
- Quando faltam informações para calcular qualquer candidato, a seleção
  anterior por demanda continua disponível, sem inventar lucro.
- O bloqueio de repetição usa o **par origem ↔ destino**, não apenas o
  destino; destinos iguais podem ser usados a partir de bases diferentes,
  desde que não constituam a mesma rota duplicada.
- A análise de rotas repetidas limita tentativas por ciclo à configuração
  `fleet_actions_per_cycle`. Cada tentativa recebe data de análise, mesmo
  quando não encontra uma alternativa lucrativa. No ciclo seguinte, rotas
  ainda não pesquisadas são priorizadas: uma rota difícil não monopoliza
  todas as pesquisas.
- Adiar análises por limite de ciclo ou desligar a análise não apaga
  propostas lucrativas já conhecidas.

### Relatório

Na aba **Rotas e aeronaves**, cada proposta apresenta destino, lucro
estimado, aumento projetado quando há referência conhecida, data do
cálculo e estado da pré-validação do ID da rota no jogo. Esses valores
não representam lucro realizado nem indicam substituição executada.

**Restrição mantida:** a troca automática real continua desabilitada.
O bot ainda não tem validação de todas as etapas de ground/reroute/rollback
do jogo; não será usada a criação de nova rota como substituição implícita
da rota ativa. A opção de despachar aeronaves continua independente das
configurações de criação/análise de rotas.


## Auditoria de 09/11/2026 — fila, dados antigos e alternativas concorrentes

O log de 02:51 registrou **18 aeronaves na página atual** e **11
rotas duplicadas no histórico acumulado, com 24 aeronaves envolvidas**.
Os números representam conjuntos diferentes: nem todas as matrículas
presentes no histórico estão visíveis na página atual. Quando a data
de `game_verified_at` expira, a posição atual **não é presumida** e o
log indica há quantos segundos a rota não é confirmada; não significa
que uma rota acabou de ser lida e já perdeu a validade.

Anteriormente o planejamento utilizava `fleet_actions_per_cycle = 2`,
compartilhado com novas rotas e compras, gerando muitos registros de
`pendente_limite_ciclo`. A nova opção **Aeronaves para analisar por
ciclo** fica em **Parâmetros → Rotas** (`route_analysis_per_cycle`),
com padrão **5** e intervalo aceito de **1 a 20**. Ela não altera o
limite `fleet_actions_per_cycle` de ordens efetivas. A análise pode
continuar com `auto_route` desligada e não envia troca de rota.

Também foi introduzida a **reserva de propostas**: o bot compara
origem↔destino (incluindo aliases IATA/ICAO/IDs) e, se uma proposta
lucrativa recente já pertence a outra aeronave, tenta outra alternativa
para não recriar as mesmas duplicidades. Por exemplo, propostas antigas
`LAX-FIH` ou `DTW-MLE` de matrículas diferentes são analisadas
como conflitos. Uma proposta sem data, já vencida (mais de **6 horas**)
ou associada a uma rota de origem que mudou não bloqueia pesquisas.

Essas reservas são apenas **planejamento local**, não reservas no jogo.
Os cálculos de lucro continuam sendo estimativas. A troca real das
rotas de aviões já atribuídos permanece protegida até existir validação
completa e segura do procedimento de substituição.
