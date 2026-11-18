# Direção 16 — implementação parcial e critérios de acabamento

Esta entrega evolui a demonstração existente. **Os protagonistas continuam sendo
modelos procedurais provisórios. Não representam o acabamento final solicitado.**
A imagem de referência e os modelos esculpidos não estavam disponíveis no projeto.

## Implementado

- Névoa baixa, figuras veladas nas laterais da cripta, correntes e materiais úmidos.
- Cinco pistas progressivas na exploração, incluindo inscrições e rastros antes
  do Arauto. Cada pista aparece uma vez por descida e fica na crônica.
- Ruídos espaciais sintetizados, intervalos de 30–65 segundos entre eventos e
  25 segundos de repouso após o combate. Não há sustos de tela inteira.
- Intensidade atmosférica independente das regras; opções locais de violência,
  flashes e tremor. Flashes e tremor começam desligados. A indicação estática de
  ataques do chefe continua visível. Violência discreta oculta marcas nas criaturas
  e suprime a animação de impacto, mantendo informações de dano.
- Vigias observam os heróis; tecelãs despertam a três casas para emboscar;
  penitentes percebem o grupo a seis casas. Esses limiares não dependem das opções
  gráficas de um jogador. As criaturas ainda utilizam as bases procedurais existentes.
- Escolhas de rosto, cabelo, constituição física, cicatriz e tatuagem, além das
  cores de pele, cabelo e equipamento já existentes. Nada altera atributos ou
  restringe classe/armas. Novos detalhes de olhos, sobrancelhas, lábios, dedos,
  correias, fivelas e placas sobrepostas.
- Prévia com luz branca neutra, giro manual/automático, pausa, zoom, enquadramento
  de rosto e corpo inteiro. O giro não salta ao soltar o mouse e cada janela de
  prévia tem seu próprio ciclo, evitando ciclos antigos sobre o novo renderer.
- Mão de apoio posicionada por cinemática inversa no cabo de armas de duas mãos
  compatíveis (espadas, hastes, cajados e armas de fogo). O arco e a corda ainda
  precisam de uma solução própria. Passada ligada à distância percorrida.
- Detalhes adicionais dos heróis são ocultos à distância ou em qualidade baixa.
  Isso é redução de detalhes, não uma cadeia completa de malhas LOD exportadas.
- Origem, motivação, medo, vínculos, segredo opcional e proposta de missão
  editáveis. Todas essas informações são explicitamente compartilhadas com a mesa.
- Proposta → aprovação do Mestre → conclusão. Editar os dados narrativos revoga
  a aprovação anterior. O servidor verifica propriedade do herói e papel do Mestre.
  Ganchos aprovados aparecem para condução narrativa na crônica durante a exploração;
  não há ainda um sistema de diálogos ramificados ou cenas de quests autorais.

## Regra opcional de tensão

Desativada por padrão. O Mestre configura CD 8–16 (padrão 12) e pode provocar um
evento; a aproximação da ponte e do selo também pode desencadeá-lo. Cada herói usa
o melhor bônus de resistência entre CON, SAB e CAR. A opção visual de terror não
altera o teste.

Falhar soma 1 tensão, até 3. Ao atingir 3, recebe −1 Defesa por até dois turnos
próprios. Novos eventos não acumulam nem renovam a penalidade. O fim do efeito
reduz a tensão para 1 e concede dois turnos de proteção. Respirar é uma escolha:
gasta a ação bônus no combate, ou é livre na exploração; reduz 1 tensão, encerra
a penalidade e concede proteção. Na exploração, a recuperação automática ocorre
a cada 30 segundos. Desligar a regra limpa o efeito. Nenhuma ação é perdida
automaticamente; não há controle da câmera, movimento forçado ou paralisia.

O Mestre continua sendo a autoridade da simulação, conforme a arquitetura
original. O estado de tensão é salvo e replicado; preferências audiovisuais são
locais. Números de combate e composição do inventário continuam em seus fluxos
originais. Alterar tensão não restaura a opção de armas de artífice por acidente.

## Ainda necessário para cumprir o pedido integralmente

- Receber a imagem de referência e produzir modelos finais com anatomia, rosto
  expressivo, cabelo, materiais PBR, desgaste e rig de produção. Não há `.glb`
  final nem importador de modelos finais nesta entrega.
- Refinar artisticamente os novos cenários procedurais de vilarejo, floresta e
  castelo. A campanha jogável está descrita em [MISSOES.md](MISSOES.md).
- Produzir monstros originais finais, IA de perseguição/emboscada mais completa e
  reações físicas à luz. A ambientação atual não equivale a esses modelos finais.
- Implementar as 21 classes que faltam e definir suas referências visuais. O
  repositório possui apenas Guerreiro, Mago e Paladino; não foram inventadas
  classes substitutas nem cadastradas opções sem regras funcionais.
- Animação facial, corrida, esquiva dedicada, canalização sustentada, interação
  detalhada com objetos, IK de pés em terreno irregular e revisão de clipping de cada arma.
  Há agora uma pose animada de interação usada nos objetivos da campanha.
  A passada e a mão de apoio melhoradas não encerram essas pendências.
- Cadeia completa de LOD, orçamento de texturas/memória e medição de FPS em
  dispositivos de referência. Não foi fixada uma meta de hardware sem requisitos.
- Diálogos/quests pessoais jogáveis e validação de equilíbrio em campanhas longas.

## Validação

```sh
node --test tests/direction.test.cjs
python -m unittest discover -s tests -p 'test_*.py' -v
```

Verificação geométrica opcional usa o mesmo Three.js r128 do jogo, baixado do
endereço CDN que já consta em `public/index.html`, como arquivo local `.cjs`:

```sh
node tests/model-smoke.cjs /caminho/three-r128.cjs
```

O teste percorre 3 protagonistas × 120 armas × 11 estados de animação, verifica
transformações finitas e distância entre mão de apoio e ponto do cabo. É uma
verificação de geometria, não comprovação de anatomia, expressividade ou ausência
de clipping. A captura visual e a revisão humana continuam necessárias.

Teste manual de regressão: criação (cores e variantes, zoom e giro), exploração
(movimento, pistas e troca de conjuntos), combate (ataque e fim de turno),
opções gráficas e uma sala com Mestre e jogador em sessões distintas. Verificar
edição pelo proprietário, proposta/aprovação da missão e persistência no servidor.

Antes de chamar os protagonistas de finalizados, revisar rosto, mãos, pés,
empunhaduras, troca de equipamento, iluminação e transições em cada classe,
ancestralidade, constituição física e família de armas, na criação, exploração e
combate. Usar a imagem de referência como critério de aprovação visual.
