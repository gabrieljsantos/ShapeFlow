import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty


def _sync_scene_units(self, context):
    context.scene.unit_settings.system = 'METRIC'
    context.scene.unit_settings.length_unit = self.length_unit


def _toggle_native_grid(self, context):
    if context.area and context.area.type == 'VIEW_3D':
        context.space_data.overlay.show_floor = self.show_native_grid
        context.space_data.overlay.show_axis_x = self.show_native_grid
        context.space_data.overlay.show_axis_y = self.show_native_grid
        context.space_data.overlay.show_axis_z = self.show_native_grid


class ShapeFlowSettings(bpy.types.PropertyGroup):
    drawing_origin: FloatVectorProperty(
        name="Creation origin",
        description="World-space origin used by ShapeFlow drawing planes",
        size=3,
        subtype='TRANSLATION',
        unit='LENGTH',
        default=(0.0, 0.0, 0.0),
    )
    show_native_grid: BoolProperty(
        name="Show Blender grid",
        description="Show Blender's native grid and axes while positioning",
        default=True,
        update=_toggle_native_grid,
    )
    move_constraint: EnumProperty(
        name="Move constraint",
        items=(
            ('X', "X", "Move only on X"), ('Y', "Y", "Move only on Y"), ('Z', "Z", "Move only on Z"),
            ('XY', "XY", "Move on XY"), ('XZ', "XZ", "Move on XZ"), ('YZ', "YZ", "Move on YZ"),
            ('XYZ', "XYZ", "Move freely using view depth"),
        ),
        default='XYZ',
    )
    copy_mode: BoolProperty(
        name="Copy",
        description="Duplicate before transforming; future Move and Rotate tools will use the same setting",
        default=False,
    )
    polygon_sides: IntProperty(
        name="Sides",
        description="Number of sides used by the Polygon tool",
        default=5,
        min=3,
        max=256,
    )
    creation_origin: EnumProperty(
        name="Creation",
        items=(
            ('CENTER', "Center", "First point is the center; drag to define radius and rotation"),
            ('DIAMETER', "Across", "First and second points define opposite sides"),
        ),
        default='CENTER',
    )
    proportional_creation: BoolProperty(
        name="Proportional",
        description="Keep equal dimensions while creating compatible shapes",
        default=True,
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
        name="Use step snapping",
        description="Quantize drawing and extrusion using ShapeFlow's configured step, independently of Blender's visible grid",
        default=True,
    )
    geometry_snap: BoolProperty(
        name="Align to geometry",
        description="Automatically align with existing vertices, edges, midpoints, and face centers",
        default=True,
    )
    grid_spacing: FloatProperty(
        name="Step size",
        description="ShapeFlow movement interval in the selected unit; this does not use Blender's visible grid",
        default=1.0,
        min=0.0001,
        precision=4,
    )
    snap_distance: IntProperty(
        name="Snap distance",
        description="Screen distance used to detect geometry guides",
        default=24,
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
            ('POLYGON', "Polygon", "Create regular polygons continuously"),
            ('EXTRUDE', "Extrude", "Push or pull faces continuously"),
            ('MOVE', "Move", "Move whole objects with snapping"),
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
