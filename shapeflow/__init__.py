"""ShapeFlow - direct modelling tools for native Blender meshes."""

bl_info = {
    "name": "ShapeFlow",
    "author": "ShapeFlow Contributors",
    "version": (0, 9, 0),
    "blender": (5, 2, 0),
    "location": "3D Viewport > Sidebar > ShapeFlow",
    "description": "Draw, extrude and split native Blender mesh faces",
    "category": "Mesh",
}

from . import properties
from .operators import CLASSES as OPERATOR_CLASSES
from .ui import CLASSES as UI_CLASSES


CLASSES = (*properties.CLASSES, *OPERATOR_CLASSES, *UI_CLASSES)
addon_keymaps = []


def register():
    for cls in CLASSES:
        __import__("bpy").utils.register_class(cls)
    properties.register_properties()
    window_manager = __import__("bpy").context.window_manager
    if window_manager.keyconfigs.addon:
        keymap = window_manager.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        item = keymap.keymap_items.new('shapeflow.pick_workplane', 'W', 'PRESS')
        addon_keymaps.append((keymap, item))


def unregister():
    for keymap, item in addon_keymaps:
        keymap.keymap_items.remove(item)
    addon_keymaps.clear()
    properties.unregister_properties()
    for cls in reversed(CLASSES):
        __import__("bpy").utils.unregister_class(cls)
