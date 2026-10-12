# Onde alterar os ícones do ShapeFlow

Os nomes de todos os ícones estão centralizados em:

`shapeflow/ui/icons.py`

Esse é o arquivo que outro chat deve alterar. A distribuição dos botões
continua em `shapeflow/ui/panel.py`.

Os ícones da barra esquerda nativa do Blender (`T`) usam uma API diferente e
ficam no dicionário `TOOLBAR_ICONS` em `shapeflow/ui/workspace_tools.py`.

## Ícones das ferramentas

Dentro de `shapeflow/ui/icons.py`, procure pelo dicionário `TOOL_ICONS` e
altere o valor associado ao identificador da ferramenta.

| Menu | Ferramenta | Identificador |
| --- | --- | --- |
| Drawing | Rectangle | `RECTANGLE` |
| Drawing | 2-Point Rectangle | `RECTANGLE_2P` |
| Drawing | Rotated Rectangle | `RECTANGLE_ROTATED` |
| Drawing | Polygon | `POLYGON` |
| Drawing | 2-Point Line | `LINE` |
| Drawing | Polyline | `POLYLINE` |
| Drawing | Ellipse / Circle | `ELLIPSE` |
| Drawing | 2-Point Arc | `ARC_2P` |
| Drawing | Center Arc | `ARC_CENTER` |
| Drawing | Pie | `PIE` |
| Drawing | 3-Point Curve | `ARC` |
| Drawing | Bezier | `BEZIER` |
| Drawing | B-Spline | `BSPLINE` |
| Drawing | Pen | `PEN` |
| Drawing | Freehand | `FREEHAND` |
| Drawing | Live Sketch | `LIVE_SKETCH` |
| Drawing | Smart Drawing | `SMART_DRAW` |
| Drawing | Crescent | `CRESCENT` |
| 3D Modeling | 3-Point Box | `BOX_3P` |
| 3D Modeling | Push/Pull | `EXTRUDE` |
| 3D Modeling | Move | `MOVE` |
| 3D Modeling | Offset | `OFFSET` |
| 3D Modeling | Fillet | `FILLET` |
| 3D Modeling | Chamfer | `CHAMFER` |
| Edição | Trim | `TRIM` |
| Edição | Extend | `EXTEND` |
| 3D Modeling | Rotate | `ROTATE` |
| 3D Modeling | Scale | `SCALE` |
| 3D Modeling | Follow Me | `FOLLOW_ME` |
| Solids | Union | `UNION` |
| Solids | Subtract | `SUBTRACT` |
| Solids | Intersect | `INTERSECT` |
| Solids | Subtração | `SOLID_TRIM` |
| Solids | Subtração invertida (ícone espelhado) | `SOLID_TRIM_REVERSE` |
| Solids | Dividir sólido | `SOLID_SPLIT` |
| Organization | Combine meshes and curves | `COMBINE` |
| Organization | Separate disconnected mesh parts | `SEPARATE` |
| Organization | Group | `GROUP` |
| Organization | Component | `COMPONENT` |
| Precision | Tape Measure | `MEASURE` |
| Precision | Protractor | `PROTRACTOR` |
| Precision | Dimensions | `DIMENSIONS` |
| Organization | Copy Series | `ARRAY_COPY` |
| Organization | Mirror | `MIRROR` |
| Organization | Solid Inspector | `SOLID_CHECK` |

Todas as ferramentas listadas acima estão implementadas; não existem mais
identificadores temporários `TIME` no registro central.

## Ícones gerais da interface

No mesmo arquivo, procure pelo dicionário `UI_ICONS`.

| Elemento | Identificador |
| --- | --- |
| Abrir workspace | `WORKSPACE` |
| Entrar no modo | `MODE_ENTER` |
| Sair do modo | `MODE_EXIT` |
| Capturar workplane | `WORKPLANE` |
| Face capturada / receiver | `FACE` |
| Grid | `GRID` |
| Copy | `COPY` |
| Menu Drawing | `DRAWING_SECTION` |
| Menu 3D Modeling | `MODELING_SECTION` |
| Menu Precision & Organization | `WORKFLOW_SECTION` |
| Ferramenta ativa | `ACTIVE` |
| Informação | `INFO` |

## Quando os PNGs estiverem prontos

Os valores atuais são nomes de ícones internos do Blender. Para imagens PNG,
o outro chat deverá implementar o carregamento com `bpy.utils.previews` em
`shapeflow/ui/icons.py` e fazer `tool_icon()` fornecer o `icon_id`. Os mesmos
identificadores devem ser mantidos para não alterar o catálogo de ferramentas.

## Outros endereços úteis

- Posição e distribuição dos botões: `shapeflow/ui/panel.py`
- Grupos, ordem e ícones da barra esquerda (`T`): `shapeflow/ui/workspace_tools.py`
- Nomes, descrições e seções: `shapeflow/tool_catalog.py`
- Registro dos painéis: `shapeflow/ui/__init__.py`
- Registro dos operadores: `shapeflow/operators/__init__.py`
- Registro geral do add-on: `shapeflow/__init__.py`
