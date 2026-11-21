# Histórico de implementações — AirlineManager4BOTWEB

Este arquivo é o registro cumulativo das entregas do roadmap. Cada entrada
informa o que foi alterado, onde, por que, validações e o que ainda **não**
foi comprovado. Não confundir implementação em código com homologação no jogo.

---

## 2026-11-21 — Entrega H01: fundação do inventário de hubs (em validação)

**Origem:** [Roadmap Hubs e Aeronaves](ROADMAP_HUBS_AERONAVES.md)  
**Branch:** `feat/roadmap-hubs-inventario-20261121`  
**Escopo:** somente leitura, perfis isolados, nenhuma compra ou realocação de aeronaves.

### Alterações realizadas

1. **`src/hub_inventory.py` — nova camada de inventário**
   - Guarda o resultado do seletor `#hubSelect` da pesquisa de rotas
     em `data/hub_inventory.json` ou `profiles/<perfil>/data/hub_inventory.json`.
   - Persiste ID interno do aeroporto, nome exibido, código IATA/ICAO
     quando comprovável, origem da leitura e horário.
   - Ignora opções vazias/placeholder; não substitui uma leitura válida
     por outra vazia, duplicada ou malformada.
   - Grava atomicamente. Falha na gravação não interrompe a operação do bot.
   - Mantém bases sem aeronaves; identifica leituras antigas (24 horas) e
     não declara que a frota consultada é completa, pois o jogo pagina a lista.
   - Só associa a aeronave a um hub se o registro **futuro** tiver
     `home_base_id`, `home_base_source="game"` e
     `home_base_verified_at` válidos. Nenhuma inferência por
     origem/destino da rota ou indicador genérico `at_base`.
   - Para somar lucro, requer `profit_route_key` igual à rota atual,
     `profit_calculated_at` e valor numérico finito; exclui estimativas
     de rota anterior e com mais de sete dias. Os campos de
     atribuição/lucro ainda não são alimentados pelo leitor do jogo.
   - Aeronaves sem prova ficam em **Base a confirmar**.

2. **`src/fleet.py` — captura oportunista sem navegação adicional**
   - Reutiliza a mesma leitura de `#hubSelect` já presente na criação de
     rotas e na análise de rotas duplicadas.
   - Não adiciona comandos ao jogo, não altera a seleção de rotas e
     não percorre todas as páginas da frota.
   - Se nenhuma dessas rotinas abrir a pesquisa, o inventário permanecerá
     aguardando fonte verificada. Não se presumem hubs a partir de
     configuração local ou de códigos de rotas.

3. **`src/web.py` — endpoint autenticado**
   - `GET /api/hubs`, sob a mesma autorização do painel web.
   - Lê exclusivamente o inventário e o cadastro de rotas locais,
     sem acessar o Selenium a partir de threads HTTP.
   - Não há `POST` para hubs nem ação de aquisição.

4. **`assets/web/index.html` — tela Hubs e Aeronaves**
   - Menu próprio e layout compatível com desktop e celular.
   - Lista bases verificadas, IDs, data da leitura, aeronaves com
     base comprovada, contagem de estimativas e lucro válido.
   - Expansão por base para consultar as relações confirmadas; grupo
     separado para aeronaves pendentes.
   - Exibe explicitamente **Sem dados** em vez de atribuir lucros ou
     aeronaves por dedução. Atualização pela API existente a cada
     15 segundos somente enquanto a tela está aberta.

5. **`tests/test_hub_inventory.py` — regressões**
   - Preservação de leitura válida, seletores inválidos, base vazia,
     vínculo não comprovado, identidade por ID, cálculo de lucro,
     invalidação de rota antiga, vencimento de dados e segregação de perfis.

### Verificações técnicas

- JavaScript completo da página: análise sintática em V8 **aprovada**
  na montagem da alteração.
- GitHub Actions após correção do teste de navegação:
  **387 testes aprovados em Python 3.10 e 387 em Python 3.13**.
  `ruff check`, `compileall` e `instalar.sh --ajuda`: aprovados nas duas versões.
  [Execução CI aprovada](https://github.com/andreypiekas/AirlineManager4BOTWEB/actions/runs/44927156193).
- Na primeira execução, um teste anterior exigia literalmente apenas
  duas telas secundárias; `tests/test_settings_workspace.py` foi atualizado
  para validar também a navegação para Hubs. A suíte completa foi reexecutada
  sem falhas.
- Teste com sessão real do Airline Manager 4: **não realizado**.
- Comparação com bases adquiridas e frota real: **não realizada**.
- Capturas de tela: **não atualizadas** nesta entrega.
- Servidor Zentria: **não implantado**; a branch principal não foi alterada.

### Limites e próximas entregas

- **H02 / Fonte autenticada:** confirmar que `#hubSelect` enumera todas as
  bases adquiridas e coletar uma amostra anonimizada. Validar a fonte
  específica de `home_base_id` por aeronave; `at_base` isolado não basta.
- **H03 / Dados financeiros:** registrar origem, rota e hora de cada
  estimativa, confirmar lucro líquido e cobertura de todo o cadastro.
- **H04 / Recomendações:** ranking da próxima aeronave com demanda
  remanescente, pista, alcance, duplicidades, escala e retorno à base.
- **H05 / Novos hubs:** confirmar oferta e preço diretamente no jogo;
  calcular custo total e payback apenas com orçamento verificado.
- **H06 / Homologação:** testes em desktop/celular, dados reais e capturas.

**Critério para promover:** CI verde, inspeção de dados reais sem
atribuições incorretas e revisão do operador. O protótipo de inventário
não deve ser apresentado como recomendador econômico pronto.
