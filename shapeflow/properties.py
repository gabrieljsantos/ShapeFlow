import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty


def _sync_scene_units(self, context):
    context.scene.unit_settings.system = 'METRIC'
    context.scene.unit_settings.length_unit = self.length_unit


class ShapeFlowSettings(bpy.types.PropertyGroup):
    copy_mode: BoolProperty(
        name="Copy",
        description="Duplicate before transforming; future Move and Rotate tools will use the same setting",
        default=False,
    )
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


@persistent
def reset_mode_on_load(_unused):
    for window_manager in bpy.data.window_managers:
        window_manager.shapeflow_mode = False
        window_manager.shapeflow_workspace = ""
        window_manager.shapeflow_active_tool = 'NONE'


@persistent
def disable_mode_after_workspace_change(_scene, _depsgraph):
    for window_manager in bpy.data.window_managers:
        if not window_manager.shapeflow_mode or not window_manager.shapeflow_workspace:
            continue
        if all(window.workspace.name != window_manager.shapeflow_workspace for window in window_manager.windows):
            window_manager.shapeflow_mode = False
            window_manager.shapeflow_workspace = ""
            window_manager.shapeflow_active_tool = 'NONE'


def register_properties():
    bpy.types.Scene.shapeflow = PointerProperty(type=ShapeFlowSettings)
    bpy.types.WindowManager.shapeflow_mode = BoolProperty(
        name="ShapeFlow Mode",
        default=False,
        options={'SKIP_SAVE'},
    )
    bpy.types.WindowManager.shapeflow_workspace = StringProperty(
        name="ShapeFlow Workspace",
        default="",
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    bpy.types.WindowManager.shapeflow_active_tool = EnumProperty(
        name="Active ShapeFlow Tool",
        items=(
            ('NONE', "None", "No ShapeFlow tool is active"),
            ('RECTANGLE', "Rectangle", "Create rectangles continuously"),
            ('EXTRUDE', "Extrude", "Push or pull faces continuously"),
        ),
        default='NONE',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    if reset_mode_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(reset_mode_on_load)
    if disable_mode_after_workspace_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(disable_mode_after_workspace_change)


def unregister_properties():
    if reset_mode_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(reset_mode_on_load)
    if disable_mode_after_workspace_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(disable_mode_after_workspace_change)
    del bpy.types.WindowManager.shapeflow_active_tool
    del bpy.types.WindowManager.shapeflow_workspace
    del bpy.types.WindowManager.shapeflow_mode
    del bpy.types.Scene.shapeflow
