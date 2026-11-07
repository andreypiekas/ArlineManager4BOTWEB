# Otimização de rotas: classificação por lucro estimado

Esta implementação usa conceitos documentados no projeto comunitário
[abc8747/am4](https://github.com/abc8747/am4), de Abraham Cheung, sob
[licença MIT](https://github.com/abc8747/am4/blob/master/LICENSE).
As fórmulas e premissas são referências; a implementação Python deste
repositório é independente e não exige o executável Rust/C++ ou o bot de Discord.

## Fluxo

1. Buscar os destinos com a mesma origem informada pela tela do jogo, nos
   limites de distância e pista definidos no painel.
2. Obter o modelo da aeronave do cache local `data/market.json`. Sem velocidade
   e consumo confiáveis, preservar o critério anterior de demanda.
3. Estimar trechos por dia usando velocidade do modelo, modo de jogo e
   permanência de seis minutos em solo.
4. Estimar passageiros vendidos por classe, **limitados à demanda do jogo**.
   Em modo de assentos automáticos, a configuração F/J/Y é apenas uma
   simulação de rentabilidade, não uma alteração imediata dos assentos reais.
5. Estimar receita com as tarifas *autoprice* do jogo nas classes Y/J/F, menos
   combustível e CO₂ calculados com os coeficientes aproximados que o bot já
   utilizava na avaliação de modelos de aeronave.
6. Ordenar as rotas por lucro diário estimado e verificar até 16 destinos;
   confirmar na página do jogo se a aeronave é compatível, a rota está livre e
   a taxa de abertura cabe no saldo antes de criar qualquer rota.
7. Se a rota já estiver ocupada, tentar as seguintes e os intervalos de
   distância menores antes de desistir.

O bot **não** altera a tarifa do jogo apenas por causa da estimativa: continua
lendo e confirmando os preços preenchidos pelo formulário do jogo. Assim,
evitamos pontuar rotas por multiplicadores de tarifa que ainda não são
aplicados ao voo real.

## Limitações e próximos passos

Os modelos lidos do mercado não incluem necessariamente motorização escolhida,
coeficiente individual de CO₂, configuração efetiva de assentos, treinamento,
índice de custo, custos de reparos/A-check ou valores atuais de taxa de rota.
A rentabilidade é uma **estimativa comparativa**, não lucro garantido.

Os destinos continuam vindo da pesquisa do próprio jogo. A distância exibida
pode ser ligeiramente diferente da distância interna (Haversine), como alerta
a documentação comunitária. A implementação não envia ordens usando distâncias
estimadas nem calcula passagens de forma independente para o formulário.

Ainda deve ser validado no jogo autenticado se cada aeronave está vinculada
à base correta na pesquisa. O seletor de base exibido pela interface é a fonte
usada na versão atual; otimização entre todas as bases requer identificação
confiável de origem e aeronave. Sem isso, não inferimos bases.

### Testar sem gastos

```bash
python -m pytest -q tests/test_route_optimizer.py
```

Habilite **Simulação (sem gastos)** no painel antes de testar com uma conta real.
Não integre esta branch à produção até verificar os registros e as escolhas
no ambiente instalado.
