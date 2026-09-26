import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty


class ShapeFlowSettings(bpy.types.PropertyGroup):
    drawing_plane: EnumProperty(
        name="Drawing Plane",
        items=(
            ('XY', "XY", "Draw parallel to the XY plane"),
            ('XZ', "XZ", "Draw parallel to the XZ plane"),
            ('YZ', "YZ", "Draw parallel to the YZ plane"),
        ),
        default='XY',
    )
    snap_enabled: BoolProperty(name="Snap", default=True)


CLASSES = (ShapeFlowSettings,)


def register_properties():
    bpy.types.Scene.shapeflow = PointerProperty(type=ShapeFlowSettings)


def unregister_properties():
    del bpy.types.Scene.shapeflow

