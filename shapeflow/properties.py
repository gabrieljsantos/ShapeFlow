import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty


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
    snap_enabled: BoolProperty(
        name="Automatic alignment",
        description="Keep ShapeFlow alignment active during normal operation",
        default=True,
    )
    grid_snap: BoolProperty(
        name="Align to grid",
        description="Automatically align drawing points to the configured grid",
        default=True,
    )
    geometry_snap: BoolProperty(
        name="Align to geometry",
        description="Automatically align with existing vertices, edges, midpoints, and face centers",
        default=True,
    )
    grid_spacing: FloatProperty(
        name="Grid spacing",
        description="Grid interval in the selected unit",
        default=1.0,
        min=0.0001,
        precision=4,
    )
    snap_distance: IntProperty(
        name="Snap distance",
        description="Screen distance used to detect geometry guides",
        default=14,
        min=4,
        max=50,
        subtype='PIXEL',
    )
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
