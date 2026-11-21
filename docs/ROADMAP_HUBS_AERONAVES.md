# Roadmap de Hubs e Aeronaves

**Em execução — primeira entrega de inventário disponível em branch de desenvolvimento.**

O objetivo é responder duas perguntas da companhia. Em quais bases vale
alocar a próxima aeronave? Qual aeroporto vale adquirir como nova base?
A primeira entrega apresenta recomendações para revisão no painel. A decisão
de compra e a escolha da base ficam com o operador.

## Tela 1 — Hubs e Aeronaves

O menu **Hubs e Aeronaves** abre a visão das bases adquiridas no perfil ativo.
Cada linha representa um aeroporto, inclusive bases sem aeronaves.

| Informação | Como será apresentada |
| --- | --- |
| Aeroporto | Nome completo e código IATA ou ICAO, quando conhecido. A identificação interna usa o ID do aeroporto no jogo. |
| Aeronaves da base | Contagem de vínculos confirmados. Ao abrir a base, será possível consultar matrícula, modelo, rota e situação das aeronaves. |
| Lucro estimado por dia | Soma das estimativas válidas das rotas ativas atribuídas à base. O painel mostra quantas rotas têm estimativa e permite ordenar as bases pelo total ou pelo lucro médio por aeronave com estimativa. |
| Próxima aeronave | Ranking de bases para receber a próxima aeronave, com modelo avaliado, rota sugerida, lucro adicional estimado e custo inicial. |

O vínculo de base vem de um dado verificável do jogo. A localização da
aeronave e as pontas da rota podem mudar ao longo da operação. Cada
aeronave será contada uma vez pelo ID no jogo, mesmo se a matrícula mudar.
Quando faltar comprovação, ela aparecerá no grupo **Base a confirmar**.

Cada estimativa de lucro deve estar vinculada à rota atual da aeronave e ter
data de cálculo. A tela indica a cobertura de cada base e separa bases sem
dados suficientes do ranking. Uma estimativa antiga de uma rota substituída
fica fora do total até novo cálculo. Valores desconhecidos aparecem como
**Sem dados**.

Para recomendar onde colocar a próxima aeronave, o bot compara o mesmo modelo
entre as bases adquiridas. A comparação considera demanda ainda disponível,
rotas ocupadas, alcance, pista mínima e o modo do jogo. A sugestão explica
se a rota é direta ou se depende de um *stopover* validado. O itinerário deve
incluir uma base adquirida como ponta, para que a aeronave possa voltar a uma
base com acesso a manutenção e A-check.

## Tela 2 — Recomendações de novos hubs

A visão **Novos hubs**, acessível a partir de **Hubs e Aeronaves**, lista
aeroportos cuja disponibilidade para compra tenha sido confirmada no jogo
para o perfil ativo. Cada opção mostra os dados abaixo.

- Nome e código do aeroporto, pista e custo de aquisição, quando disponíveis.
- Modelo e rota usados na projeção, com demanda e limitações relevantes.
- Lucro operacional diário projetado, investimento inicial, dias estimados
  para recuperar o investimento e situação em relação à reserva de caixa.
- Data de verificação e dados pendentes para validar a recomendação.

Para comparar aeroportos, a primeira versão usa um cenário inicial de uma
aeronave do mesmo modelo, com uma rota viável a partir do hub após a compra.
O lucro adicional projetado usa a estimativa existente de receita menos
combustível e CO₂. O investimento inicial soma o preço do hub, o da aeronave,
a taxa de abertura de rota e o custo de vaga de hangar quando necessário.
A tela explicita quais custos ficam fora da estimativa, como reparos e A-checks.

O ranking mostra primeiro as opções com lucro positivo e custo completo que
cabem no saldo disponível acima da reserva de caixa. Entre elas, a ordem
padrão é por lucro diário projetado, com opção de ordenar pelo prazo de
retorno. O prazo é o investimento inicial dividido pelo lucro diário
projetado. Candidatos com preço, demanda ou saldo pendente ficam identificados
como **Dados a confirmar**. Se o jogo não expuser um catálogo comprovável de
bases adquiríveis, a tela mostra **Disponibilidade de compra a verificar**.

## Entregas em ordem

1. **Confirmar as fontes no jogo.** Em uma sessão autenticada e de leitura,
   identificar as bases adquiridas, o vínculo de base por aeronave, a lista
   de aeroportos compráveis e os respectivos preços. Verificar se o jogo
   permite pesquisar demanda e pista com o hub candidato como origem antes
   da compra. Validar a cobertura da frota, inclusive listas paginadas, e
   coletar exemplos anonimizados para os testes.
2. **Inventário, rentabilidade e primeira tela.** Persistir as leituras por
   perfil com fonte e horário. Cruzar os IDs de aeroportos e aeronaves com o
   cadastro de rotas. Agregar frota e estimativas por base e publicar a visão
   de hubs adquiridos. O painel lê os dados locais pela API autenticada.
   As consultas ao jogo ocorrem pela sessão do bot, com limite por ciclo.
3. **Recomendações de expansão.** Usar o mesmo estimador de rotas para
   recomendar o destino da próxima aeronave nas bases atuais e comparar
   aeroportos candidatos. Publicar a visão **Novos hubs**, com explicação
   do cenário, investimento, retorno e dados pendentes.
4. **Validação e documentação.** Conferir o painel em desktop e celular,
   comparar as contagens com o jogo em modo de leitura e atualizar README e
   capturas com dados de demonstração.

Depois de confirmar as fontes, a tela de bases adquiridas e o motor de
recomendações podem avançar em paralelo sobre os mesmos dados por perfil.

## Pontos de partida no código

- [Frota e pesquisa de rotas](../src/fleet.py) já consultam o seletor de bases
  adquiridas e a demanda das rotas. [Catálogo de aeroportos](../src/airport_catalog.py)
  ajuda a reconciliar códigos IATA e ICAO com IDs do jogo.
- [Manutenção](../src/maintenance.py) informa se a aeronave está em uma base
  no momento da leitura. A origem e o destino do
  [cadastro de rotas](../src/route_registry.py) complementam a análise da
  malha. O vínculo individual a uma base ainda precisa de confirmação.
- [Estimador de rotas](../src/route_optimizer.py) e
  [mercado de aeronaves](../src/market.py) fornecem a base para comparar
  os cenários. Os custos de compra de hubs exigem uma fonte própria.
- [API e controle de acesso do painel](../src/web.py) e
  [interface web](../assets/web/index.html) dão o padrão para as duas visões.

## Critérios de aceite

- A lista coincide com os hubs adquiridos no perfil ativo. Inclui uma base
  vazia e mantém separadas as aeronaves cuja base ainda precisa de confirmação.
- A contagem permanece correta quando uma rota liga dois hubs, uma aeronave
  pousa fora da sua base ou uma matrícula muda. Leituras parciais ou antigas
  aparecem com sua cobertura e horário.
- O operador consegue identificar as bases mais lucrativas, abrir as rotas
  que compõem o total e entender em qual base a próxima aeronave tem maior
  potencial pelas premissas exibidas.
- A comparação de novos hubs explica os custos, o retorno e a compatibilidade
  da rota. Preços ausentes, lucro negativo e saldo abaixo da reserva são
  tratados explicitamente.
- A navegação funciona em desktop e celular, com dados isolados por perfil.
  As duas visões funcionam a partir da última leitura disponível e só
  oferecem ações de consulta e comparação.


## Estado de execução (21/11/2026)

- [x] Inventário local por perfil baseado no seletor de hubs já consultado,
      com validação de IDs e horário da fonte.
- [x] API de consulta autenticada e tela inicial de Hubs e Aeronaves.
- [x] Testes unitários adicionados para fonte, identidade, estimativas e perfis.
- [ ] Confirmar em sessão autenticada que o seletor enumera integralmente
      as bases adquiridas.
- [ ] Confirmar campo de base própria **por aeronave**, inclusive em
      páginas diferentes e para bases sem aeronaves.
- [ ] Coletar e relacionar estimativas válidas de lucro à rota vigente.
- [ ] Implantar ranking de alocação de próxima aeronave, novos hubs e payback.
- [x] Executar CI da entrega H01: 387 testes aprovados em Python 3.10 e 3.13.
- [ ] Homologar contra o jogo, validar mobile com dados reais e atualizar capturas.

A primeira tela deliberadamente mostra dados desconhecidos como
**Sem dados** ou **Base a confirmar**. Não representa uma implementação
completa das etapas 1 e 2. Ver o [histórico técnico](HISTORICO_IMPLEMENTACOES.md).
