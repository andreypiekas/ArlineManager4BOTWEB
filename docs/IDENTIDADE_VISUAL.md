# AM/04 — Identidade visual e contratos de interface

## Conceito

**Torre de Controle** é o novo sistema visual do Airline Manager 4 Bot. Não é um
painel de cartões genérico: foi construído como um terminal de operações,
com um trilho de controle persistente, hierarquia editorial, telemetria
instrumental e registro de eventos centralizado. Os dados reais continuam
chegando pelos mesmos endpoints e os botões executam as mesmas ações.

### Linguagem visual

| Elemento | Papel |
| --- | --- |
| Grafite profundo (#0B1014) | Superfície de operação contínua, sem ruído |
| Verde-sinal (#C8FC79) | Ação primária e identificação do sistema |
| Ciano técnico (#76E8DF) | Telemetria, seções e evidência de dados |
| Laranja de atenção (#FFBE70) | Transições e avisos |
| Vermelho operacional (#FF827B) | Erros e parada |
| Tipografia condensada | Números, manchetes e identificação |
| Monoespaçada | Dados, códigos, horários, filtros e rótulos |

No painel web não há dependência de fontes remotas, frameworks CSS ou CDN.
A aplicação desktop CustomTkinter compartilha a paleta por meio de
`assets/theme.json`, com modo escuro como padrão para novas instalações.

### Organização do painel

- **Trilho lateral:** estado do serviço, tempo até o próximo ciclo, simulação,
  navegação e comandos principais, sem misturar operações com configurações.
- **Telemetria:** seis instrumentos com prioridade visual para saldo, seguido
  de reputação, combustível, CO₂, frota e meta.
- **Centro de operações:** console de eventos com filtro de categoria e
  parâmetros divididos em Mercado, Frota, Aeronaves e Opções.
- **Dispositivos móveis:** o trilho passa para uma faixa de comandos e
  os instrumentos reorganizam suas colunas em telas estreitas.

### Comportamento preservado

Os IDs de DOM usados pelo Javascript e todos os endpoints operacionais
continuam iguais: `/api/status`, `/api/log`,
`/api/settings` e `/api/control`. O código da
navegação e as configurações persistidas não dependem da apresentação.

## Idiomas

O texto **de origem da aplicação** é agora português brasileiro.
O inglês opcional é um mapeamento explícito de textos pt-BR para en
(`src/i18n.py`). Não se usa mais espanhol como idioma-fonte do painel.

Continuam intocados os dados que não são texto de interface:

- IDs, nomes de campos e endpoints do Airline Manager 4.
- Seletores XPath/CSS e variáveis JavaScript lidas da página do jogo.
- Valores legados aceitos na configuração e nomes técnicos de categorias de log.
- Mensagens devolvidas diretamente pelo jogo, que seguem o idioma selecionado
  na conta do jogador.

Os testes automatizados verificam os controles do painel, os IDs DOM,
as principais traduções, o JavaScript e os nomes exibidos nos logs.

## Atualização e imagens

As capturas históricas presentes em `screenshots/` representam a
interface anterior. Devem ser regeneradas somente em um dispositivo com o
bot e o navegador instalados, após a atualização. Não são utilizadas
como dependências para renderizar o novo painel.

Antes de atualização em um servidor, faça backup dos arquivos locais de
configuração. O código não sobrescreve `config/secrets.ini`,
`config/settings.ini`, sessões ou os dados salvos pela automação.
