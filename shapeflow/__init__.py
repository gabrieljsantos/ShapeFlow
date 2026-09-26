"""ShapeFlow - direct modelling tools for native Blender meshes."""

bl_info = {
    "name": "ShapeFlow",
    "author": "ShapeFlow Contributors",
    "version": (0, 8, 0),
    "blender": (5, 2, 0),
    "location": "3D Viewport > Sidebar > ShapeFlow",
    "description": "Draw, extrude and split native Blender mesh faces",
    "category": "Mesh",
}

from . import properties
from .operators import CLASSES as OPERATOR_CLASSES
from .ui import CLASSES as UI_CLASSES


CLASSES = (*properties.CLASSES, *OPERATOR_CLASSES, *UI_CLASSES)


def register():
    for cls in CLASSES:
        __import__("bpy").utils.register_class(cls)
    properties.register_properties()


def unregister():
    properties.unregister_properties()
    for cls in reversed(CLASSES):
        __import__("bpy").utils.unregister_class(cls)
