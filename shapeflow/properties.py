import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty


def _sync_scene_units(self, context):
    context.scene.unit_settings.system = 'METRIC'
    context.scene.unit_settings.length_unit = self.length_unit


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
    length_unit: EnumProperty(
        name="Unit",
        description="Unit used by typed dimensions",
        items=(
            ('MILLIMETERS', "mm", "Typed values are millimeters"),
            ('CENTIMETERS', "cm", "Typed values are centimeters"),
            ('METERS', "m", "Typed values are meters"),
        ),
        default='MILLIMETERS',
        update=_sync_scene_units,
    )


CLASSES = (ShapeFlowSettings,)


def register_properties():
    bpy.types.Scene.shapeflow = PointerProperty(type=ShapeFlowSettings)


def unregister_properties():
    del bpy.types.Scene.shapeflow
