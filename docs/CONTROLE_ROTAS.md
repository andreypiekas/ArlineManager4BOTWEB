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

A correção automática só altera o jogo quando, na mesma verificação:

1. A origem e o destino atuais foram verificados por identificadores do jogo.
2. O jogo confirma **explicitamente** que a aeronave está em sua base.
3. O modelo tem dados técnicos suficientes para estimar lucro positivo.
4. A nova rota está livre nos dois sentidos segundo o histórico e o jogo.
5. O jogo indica a aeronave como elegível para a rota proposta.
6. A taxa não compromete a reserva de caixa; o formulário e a ordem são
   confirmados pelo fluxo de criação do jogo.

Se faltar qualquer evidência, a tela mostra um motivo de pendência e, quando
possível, a alternativa calculada. O bot **não altera rotas por dedução**.

O modo **Simulação (sem gastos)** calcula e registra propostas, sem enviar
pedidos de nova rota.

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
