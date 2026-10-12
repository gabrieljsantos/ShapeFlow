# ShapeFlow: mapa de intenções e fluxos de uso

Este documento reconstrói os objetivos expressos nas conversas do projeto e os relaciona às ferramentas presentes no código. A referência principal de histórico é a conversa **“Organizar ferramentas reutilizáveis”**. Os fluxos abaixo foram conferidos também no catálogo, painel, propriedades e operadores atuais.

## A ideia central

ShapeFlow busca trazer para a viewport do Blender um fluxo de desenho e modelagem direta inspirado no SketchUp: escolher um plano, traçar perfis com precisão, transformar perfis em volume, editar faces e arestas e combinar sólidos. A implementação usa objetos `Mesh` e `Curve` nativos do Blender; várias operações são não destrutivas e ficam como modificadores editáveis.

## Preparação comum

1. Abra a Viewport 3D e entre em **ShapeFlow Mode** no painel ShapeFlow (`N` → ShapeFlow).
2. Escolha um plano: `AUTO` acompanha o gesto/eixos; `FACE` usa um plano local capturado de uma face; os planos globais permitem desenhar em XY/XZ/YZ.
3. Para `FACE`, passe o cursor sobre a face desejada e pressione **W** (ou use **W Capture hovered face**). Isso captura a orientação da face como plano de desenho; não seleciona a face para edição.
4. Ajuste o cursor de construção, se necessário. O controle **Grid** mostra/oculta a grade visual nativa do Blender; **Incremental** (`grid_snap`) quantiza deslocamentos e dimensões pelo passo configurado. São controles diferentes.
5. **Magnetic** aproxima pontos da geometria existente (vértices, meios, arestas e faces); `Alt` suspende temporariamente os snaps durante as ferramentas que suportam esse atalho.
6. Escolha **Separate** para criar outro objeto ou **Embedded** para incorporar o perfil compatível na malha receptora da face capturada.

## Fluxos principais

### 1. Desenhar um perfil e extrudar — equivalente ao fluxo SketchUp de face + Push/Pull

1. Capture uma face com **W** ou selecione um plano global.
2. Escolha Rectangle, 2-Point Rectangle, Polygon, Circle/Ellipse, Arc/Pie, Line/Polyline ou uma ferramenta de curvas.
3. Clique os pontos na viewport. Use snapping, incremento e entrada numérica para posicionar ou dimensionar.
4. Com saída **Embedded**, linhas e curvas compatíveis gravam seu contorno na face receptora, dividindo-a em faces; com **Separate**, o perfil fica em objeto separado.
5. Escolha **Push/Pull**, clique numa face, mova para definir a distância e confirme. `Enter`/clique confirma e `Esc` cancela ou encerra conforme a etapa indicada na barra de status.

Esse é o fluxo para desenhar formas sobre uma face existente e depois puxar/empurrar regiões. Para traços abertos, use Line/Polyline; perfis fechados podem gerar faces que recebem Push/Pull.

### 2. Dividir uma face com um desenho

Use um perfil incorporado (Embedded) numa face. O contorno do desenho subdivide a malha receptora em faces, permitindo trabalhar cada região separadamente e extrudar apenas a área desejada. Isso é diferente da ferramenta booleana **Intersect**, que conserva o volume comum de dois sólidos.

### 3. Booleanas de sólidos: união, subtração e interseção

1. Selecione dois objetos `Mesh` que se sobreponham.
2. Deixe ativo o objeto que receberá o modificador; o outro será o operand/cortador.
3. Escolha **Union**, **Subtract** ou **Intersect**.
4. Ajuste ou aplique o `Boolean Modifier` nativo quando quiser.

`Intersect` mantém apenas o volume comum. **Solid Trim** corta um sólido usando outro; **Solid Split** cria os resultados complementarmente interno e externo. Essas ferramentas preservam o caráter editável dos modificadores quando aplicável.

### 4. Editar contornos e arestas

- **Offset**: passe o cursor sobre uma face, arraste para criar um contorno interno; útil para molduras e paredes.
- **Fillet / Chamfer**: passe sobre uma aresta e arraste ou digite o tamanho; Fillet arredonda, Chamfer corta em chanfro.
- **Trim / Extend**: selecione a curva de assunto e a curva de limite (use `Shift` para acumular seleção), escolha qual extremidade editar e apare ou estenda até o cruzamento.
- **Follow Me**: use a curva ativa como caminho e a outra seleção como perfil para varrer uma seção ao longo do trajeto.

### 5. Posicionar e transformar com precisão

- **Move**: arraste objetos ou componentes; `Ctrl` durante a captura limita a deformação a vértice, aresta ou face. Restrições X/Y/Z e planos XY/XZ/YZ estão no painel.
- **Rotate**: defina pivô, direção de referência e direção final no plano ativo; pode capturar uma face com `W`.
- **Scale**: escala por fator, porcentagem ou dimensão final desejada.
- **Copy Series**: cria repetição linear ou radial com quantidade, eixo e espaçamento/ângulo.
- **Mirror**: adiciona modificador de espelho não destrutivo.
- **Group / Component**: agrupa sob um Empty nativo ou cria cópia vinculada que compartilha os dados da malha.

### 6. Medir e documentar

- **Tape Measure**: indique dois pontos; a leitura aparece durante a operação e pode virar guia editável.
- **Protractor**: indique centro, direção de referência e direção final; pode criar uma guia angular.
- **Dimensions**: cria cotas lineares, angulares, de raio ou diâmetro com objetos nativos editáveis.
- **Solid Inspector**: analisa malha aberta, não manifold, elementos soltos/duplicados/degenerados e faces invertidas.

## Ferramentas de desenho disponíveis

O catálogo atual inclui retângulos (canto, centro, 2 pontos e rotacionado), polígonos, linha e polilinha, elipses/círculos, arcos, setor circular, Bézier, B-Spline/NURBS, Caneta, Mão Livre, Live Sketch, Desenho Inteligente e Crescente. A maioria das ferramentas planares compartilha o cursor 3D, planos e snapping do núcleo ShapeFlow.

## Distinções que o tutorial deve deixar claras

| Termo/controle | O que faz |
| --- | --- |
| **W / Capture Face** | Captura a orientação da face sob o cursor como plano de trabalho local. |
| **Grid** | Exibe/oculta grade e eixos visuais nativos do Blender. |
| **Incremental** | Restringe movimento/dimensões a intervalos numéricos configurados. |
| **Magnetic** | Atrai o cursor a elementos da geometria existente. |
| **Embedded** | Incorpora perfis compatíveis à malha receptora e divide a face. |
| **Intersect** | Booleana de volume compartilhado entre dois sólidos. |
| **Solid Split** | Separa o resultado em partes internas e externas ao cortador. |

## Escopo e pontos a validar antes de gravar o tutorial

- O painel atual expõe **Embedded** e mostra o receptor da face; confirme visualmente quais tipos de curva/perfil são aceitos em cada modo antes de prometer que todo desenho vira face.
- `W` captura o plano de trabalho nas ferramentas de desenho, Move, Scale, Rotate e Push/Pull. Comportamentos e atalhos podem variar conforme a ferramenta e o estágio modal; a barra de status é a referência durante a ação.
- O controle de incremento é chamado de `grid_snap` no código, mas não depende da grade visual. No painel, a opção aparece em **Alignment settings**.
- A gravação/estado atual do projeto contém alterações locais não commitadas; este mapa documenta o estado observado, não uma garantia de release.
