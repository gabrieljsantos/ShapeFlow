# Manifesto de implementação: modos de desenho 2D

## Objetivo

Separar as ferramentas de desenho 2D em grupos com modos próprios e pré-visualização no plano de construção ativo. Os modos descritos neste documento são implementados no add-on; este arquivo serve como especificação interna.

## Modos

1. **Polígono regular pelo vértice** — clicar no centro e arrastar até um vértice. A distância centro-vértice define o raio circunscrito. Os vértices ficam igualmente espaçados. Preservar o controle atual do número de lados.
2. **Polígono regular pela aresta** — clicar no centro e arrastar até o ponto médio de uma aresta. Essa distância define o raio interno (apotema). Os lados e vértices ficam distribuídos uniformemente; manter orientação consistente com o cursor.
3. **Polígono por vértices livres** — clicar no centro para iniciar e clicar sucessivamente nos vértices desejados. O cursor pré-visualiza o próximo vértice e cada clique confirma sua posição independente. Com três ou mais vértices, confirmar para fechar o contorno e criar o perfil/face coplanar.

## Interação e compatibilidade

- Oferecer os três modos como subopções da ferramenta Polígono.
- Usar o plano de construção ativo, snap, guias e entrada numérica existentes.
- Exibir geometria em azul e a ação em laranja.
- Ícone geral Polígono: somente a silhueta azul, sem raios ou pontos.
- Ícone Regular pelo vértice: um raio laranja do centro até um vértice.
- Ícone Regular pela aresta: um raio laranja do centro até o meio de uma aresta.
- Ícone Vértices livres: raios laranja ligando o centro a todos os vértices.
- `Esc` cancela a operação. `Enter` fecha o contorno livre com pelo menos três vértices; validar a geometria antes de criar a face.
- Os modos usam o operador modal de desenho, plano ativo, captura, snap, preview e criação de perfil nativo.

## Lua por dois arcos

- Primeiro e segundo cliques definem as duas extremidades e formam a corda comum da lua.
- Terceiro clique define a curvatura do primeiro arco.
- O segmento entre os dois primeiros pontos é a corda. A indicação da curvatura parte de seu ponto médio e vai até o terceiro ponto.
- O primeiro arco passa pelos extremos da corda e pelo terceiro ponto. O segundo arco usa uma curvatura interna derivada do vetor ponto médio–terceiro ponto para fechar o crescente.
- A pré-visualização mostra a corda entre os dois primeiros pontos e a indicação do ponto médio até o terceiro; os pontos de ação aparecem em laranja e o perfil em azul.
- `Esc` cancela. Confirmar o perfil fechado cria a forma coplanar no plano de construção ativo.
- O ícone `tool-crescent-2arc` representa os dois extremos da corda e o terceiro ponto, com uma linha da corda e outra partindo do ponto médio até o terceiro ponto.

## Artefatos de interface

- Ícone pai: `tool-polygon`.
- Ícone filho pelo vértice: `tool-polygon-vertex`.
- Ícone filho pela aresta: `tool-polygon-edge`.
- Ícone filho de vértices livres: `tool-polygon-free-vertices`.
- SVG e PNG espelhados em `shapeflow/assets/` e `site/dist/assets/`.
- Catálogo: cards em `site/dist/index.html`; opções novas marcadas “Em estudo”.

## Modos de Retângulo

A ferramenta principal se chama **Retângulo** e usa somente o contorno azul no ícone. Suas opções ficam agrupadas como filhas, com a descrição em cada modo:

1. **Canto a canto** — dois cantos opostos definem o perfil retangular.
2. **Quadrado regular** — usa a criação proporcional já existente para manter os lados iguais.
3. **Por dois pontos** — conserva a ferramenta existente, com largura e depois altura a partir da origem.
4. **Rotacionado** — fluxo de produção em três pontos: (1) clicar no primeiro canto; (2) clicar no segundo ponto para definir a rotação/direção da base; (3) mover e clicar no terceiro ponto para definir a largura perpendicular do retângulo rotacionado. A direção definida no segundo ponto determina o eixo da base; a largura do terceiro ponto é projetada no eixo perpendicular. Os cantos permanecem a 90 graus, e o quarto canto é calculado para fechar o retângulo no plano ativo.
5. **Espelhado por um ponto** — usa o centro como origem e expande o perfil simetricamente; corresponde ao modo CENTER existente.
6. **Espelhado por dois pontos** — modo listado no catálogo para definir a extensão em dois pontos e manter a expansão simétrica pelo centro; sua regra de interação ainda precisa ser fechada antes de entrar no operador.

Os cinco modos existentes aparecem como modos disponíveis. O espelhado por dois pontos permanece documentado enquanto a regra de interação é definida.

## Hierarquia visual no catálogo

- Ícone geral e nome destacado aparecem lado a lado acima dos modos filhos, sem descrição nem container externo.
- Os modos filhos aparecem abaixo, com seus próprios ícones, nomes e descrições.
- Aplicar a mesma apresentação aos grupos Retângulo e Polígono; não exibir o selo “Modo”.
- O ícone do Retângulo rotacionado mostra os três pontos clicados: canto inicial, direção da base e largura perpendicular; o quarto canto fica implícito e os quatro cantos mantêm 90 graus.


## Modos de Elipse e Círculo

Separar em dois grupos pais: **Elipse** e **Círculo**. Cada grupo tem um ícone geométrico azul próprio, sem pontos de ação. Os modos filhos ficam dentro de seu grupo, com ícones, nomes e descrições. Elipse e círculo pertencem ao grupo de ferramentas de desenho 2D.

1. **Elipse pelo centro** — primeiro clique define o centro; o segundo define o raio da largura; o terceiro define o raio da altura. Os dois raios são independentes e orientados pelos eixos do plano ativo.
2. **Elipse por focos** — primeiro e segundo cliques definem os focos F1 e F2; o terceiro escolhe um ponto P sobre a curva. A elipse é definida pela soma constante das distâncias a F1 e F2, com `2a = distância(F1, P) + distância(F2, P)`. O ponto P deve ficar fora do segmento entre os focos para formar uma elipse não degenerada.
3. **Elipse por eixo e altura** — primeiro e segundo cliques definem extremidades opostas do eixo; o terceiro define a altura perpendicular. Manter os eixos ortogonais.
4. **Círculo pelo centro** — primeiro clique define o centro; o segundo define o raio.
5. **Círculo por diâmetro** — dois cliques definem os extremos opostos do diâmetro.

O grupo **Elipse** contém os três modos de elipse; **Círculo** contém os dois modos circulares.

## Artefatos de círculo e elipse

- Ícone pai Elipse: `tool-ellipse` (somente o contorno azul de uma elipse).
- Ícone pai Círculo: `tool-circle` (somente o contorno azul de um círculo).
- Ícones filhos: `tool-ellipse-center`, `tool-ellipse-foci`, `tool-ellipse-axis`, `tool-circle-center` e `tool-circle-diameter`.
- SVG e PNG espelhados entre `shapeflow/assets/` e `site/dist/assets/`.

## Grupos de desenho 2D

Organizar as ferramentas de desenho 2D em grupos pais, mantendo os cartões e as descrições individuais:

- **Retângulo**: canto a canto, quadrado regular, por dois pontos, rotacionado e modos espelhados.
- **Polígono**: regular pelo vértice, regular pela aresta e vértices livres.
- **Elipse** e **Círculo**: métodos listados acima.
- **Linhas e caminhos**: Linha e Polilinha.
- **Arcos e setores**: Arco por 2 pontos, Arco pelo centro, Setor circular, Arco por 3 pontos e Lua por dois arcos de 3 pontos.
- **Curvas**: Curva Bézier, Curva B-Spline, Caneta, Mão livre, Esboço ao vivo e Desenho inteligente.

Os grupos usam ícone pai azul sem indicação de ação. Modos ainda não implementados permanecem identificados como “Em estudo”.
