"""Print a ShapeFlow installation and workspace diagnostic in Blender's console."""

import importlib.util
import sys

import bpy


_report = ["========== ShapeFlow diagnostic =========="]


def _line(label, value):
    _report.append(f"{label}: {value}")


_line("Blender", f"{bpy.app.version_string} ({bpy.app.binary_path})")

addon = bpy.context.preferences.addons.get("shapeflow")
_line("Complemento habilitado nas preferências", "SIM" if addon else "NÃO")

module = sys.modules.get("shapeflow")
if module is None:
    try:
        spec = importlib.util.find_spec("shapeflow")
    except Exception as error:
        spec = None
        _line("Erro procurando módulo", repr(error))
    _line("Módulo encontrado no Python", "SIM" if spec else "NÃO")
    _line("Caminho encontrado", spec.origin if spec else "indisponível")
else:
    _line("Módulo carregado de", getattr(module, "__file__", "caminho indisponível"))
    _line("Versão do módulo", getattr(module, "bl_info", {}).get("version", "indisponível"))

workspaces = list(bpy.data.workspaces)
_line("Workspaces existentes", ", ".join(workspace.name for workspace in workspaces) or "nenhum")
_line("Workspace ativo nesta janela", bpy.context.workspace.name if bpy.context.workspace else "indisponível")
shape_workspace = bpy.data.workspaces.get("ShapeFlow")
_line("Workspace chamado ShapeFlow existe", "SIM" if shape_workspace else "NÃO")

panel = getattr(bpy.types, "SHAPEFLOW_PT_main", None)
_line("Painel ShapeFlow registrado", "SIM" if panel else "NÃO")
if panel:
    try:
        _line("Painel visível no workspace atual (poll)", "SIM" if panel.poll(bpy.context) else "NÃO")
    except Exception as error:
        _line("Erro ao avaliar visibilidade do painel", repr(error))

for prop in ("shapeflow_mode", "shapeflow_workspace", "shapeflow_active_tool"):
    exists = prop in bpy.types.WindowManager.bl_rna.properties
    _line(f"Propriedade runtime {prop}", "registrada" if exists else "ausente")

if hasattr(bpy.context.window_manager, "shapeflow_mode"):
    _line("Modo ShapeFlow ativo", "SIM" if bpy.context.window_manager.shapeflow_mode else "NÃO")
    _line("Workspace associado ao modo", bpy.context.window_manager.shapeflow_workspace or "nenhum")

view_areas = []
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            view_areas.append((window.workspace.name, space.show_region_toolbar, space.show_region_ui))
_line("Áreas Vista 3D (workspace, toolbar esquerda, painel N)", repr(view_areas) if view_areas else "nenhuma")

_report.append("=========== fim do diagnóstico ===========")
report_text = bpy.data.texts.get("ShapeFlow Diagnostic") or bpy.data.texts.new("ShapeFlow Diagnostic")
report_text.clear()
report_text.write("\n".join(_report))
print("\n".join(_report))

if bpy.context.area and bpy.context.area.type == 'TEXT_EDITOR':
    bpy.context.area.spaces.active.text = report_text
