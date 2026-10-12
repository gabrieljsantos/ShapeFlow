import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty

from .tool_catalog import active_tool_items


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
    axis_cursor: BoolProperty(
        name="Axis navigation",
        description="Move the construction cursor incrementally along projected axes; disable for continuous positioning on the drawing plane",
        default=True,
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
    scale_input_mode: EnumProperty(
        name="Scale input",
        items=(
            ('FACTOR', "Factor", "Use a multiplier such as 1.5"),
            ('PERCENT', "Percent", "Use a percentage such as 150"),
            ('DIMENSION', "Exact size", "Scale uniformly so the selected dimension matches an exact requested size"),
        ),
        default='FACTOR',
    )
    rotation_increment_enabled: BoolProperty(
        name="Angular increment",
        description="Quantize rotation using the configured angular step",
        default=True,
    )
    rotation_pivot_mode: EnumProperty(
        name="Rotation pivot",
        items=(
            ('PICKED', "Picked point", "Choose any snapped geometry point as the rotation origin"),
            ('CENTER', "Object center", "Use the active object's bounding-box center as the rotation origin"),
        ),
        default='PICKED',
    )
    rotation_increment: FloatProperty(
        name="Angle step", description="Rotation increment in degrees",
        default=15.0, min=0.1, max=180.0, precision=2,
    )
    scale_axis: EnumProperty(
        name="Measured size",
        items=(
            ('MAX', "Largest", "Use the largest world bounding-box dimension"),
            ('X', "X", "Use world-space width"),
            ('Y', "Y", "Use world-space depth"),
            ('Z', "Z", "Use world-space height"),
        ),
        default='MAX',
    )
    scale_target_size: FloatProperty(
        name="Target size",
        description="Exact final size in the selected ShapeFlow unit",
        default=1000.0,
        min=0.0001,
        precision=4,
    )
    array_mode: EnumProperty(
        name="Series type",
        items=(
            ('LINEAR', "Linear", "Use Blender's non-destructive Array modifier"),
            ('RADIAL', "Radial", "Create linked instances rotated around the ShapeFlow cursor"),
        ),
        default='LINEAR',
    )
    array_axis: EnumProperty(
        name="Series axis",
        items=(('X', "X", "Use X axis"), ('Y', "Y", "Use Y axis"), ('Z', "Z", "Use Z axis")),
        default='X',
    )
    array_count: IntProperty(
        name="Count", description="Total number of objects including the original",
        default=3, min=2, max=1000,
    )
    array_spacing: FloatProperty(
        name="Spacing", description="Constant distance between linear copies in the selected unit",
        default=1000.0, precision=4,
    )
    array_angle: FloatProperty(
        name="Step angle", description="Rotation in degrees between radial linked copies",
        default=45.0, min=-360.0, max=360.0, precision=2,
    )
    mirror_axis: EnumProperty(
        name="Mirror axis",
        items=(('X', "X", "Mirror on local X"), ('Y', "Y", "Mirror on local Y"), ('Z', "Z", "Mirror on local Z")),
        default='X',
    )
    measure_create_guide: BoolProperty(
        name="Create guide",
        description="Keep each measurement as an editable native non-rendering Curve",
        default=False,
    )
    last_measure: FloatProperty(
        name="Last measurement", default=0.0, min=0.0,
        unit='LENGTH', precision=6, options={'HIDDEN'},
    )
    protractor_create_guide: BoolProperty(
        name="Create angle guide",
        description="Keep the measured rays as an editable native non-rendering Curve",
        default=False,
    )
    last_angle: FloatProperty(
        name="Last angle", default=0.0, min=0.0, max=3.141592653589793,
        subtype='ANGLE', unit='ROTATION', precision=4, options={'HIDDEN'},
    )
    dimension_type: EnumProperty(
        name="Dimension type",
        items=(
            ('LINEAR', "Linear", "Distance between two points"),
            ('ANGULAR', "Angular", "Angle from center and two directions"),
            ('RADIUS', "Radius", "Radius between center and rim"),
            ('DIAMETER', "Diameter", "Twice the distance between center and rim"),
        ),
        default='LINEAR',
    )
    inspection_summary: StringProperty(
        name="Inspection result", default="Not inspected", options={'SKIP_SAVE'},
    )
    curve_edit_side: EnumProperty(
        name="Curve end",
        items=(
            ('START', "Start", "Trim or extend the first endpoint"),
            ('END', "End", "Trim or extend the last endpoint"),
        ),
        default='END',
    )
    copy_mode: BoolProperty(
        name="Copy",
        description="Duplicate the selected object before moving it or pushing/pulling a face",
        default=False,
    )
    extrusion_mode: EnumProperty(
        name="Extrusion mode",
        items=(
            ('SIMPLE', "Simple", "Extrude without resolving contact or coincident faces"),
            ('FUSE', "Fuse", "Remove matching contact faces and weld the resulting solid"),
        ),
        default='SIMPLE',
    )
    follow_me_caps: BoolProperty(
        name="Close sweep ends",
        description="Use Blender Curve fill caps at the start and end of the sweep",
        default=True,
    )
    polygon_sides: IntProperty(
        name="Sides",
        description="Number of sides used by the Polygon tool",
        default=5,
        min=3,
        max=256,
    )
    stroke_spacing: IntProperty(
        name="Stroke spacing", description="Minimum pointer distance in pixels between freehand samples",
        default=4, min=1, max=32, subtype='PIXEL',
    )
    live_smoothing: IntProperty(
        name="Live smoothing", description="Number of smoothing passes applied to Live Sketch",
        default=2, min=0, max=4,
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
    creation_output: EnumProperty(
        name="Creation output",
        items=(
            ('SEPARATE', "Separate", "Create an independent mesh object"),
            ('EMBEDDED', "Embedded", "Imprint supported lines and curves into the captured receiver face"),
        ),
        default='SEPARATE',
    )
    workplane_object: StringProperty(default="", options={'HIDDEN'})
    workplane_face_index: IntProperty(default=-1, options={'HIDDEN'})
    drawing_plane: EnumProperty(
        name="Drawing Plane",
        items=(
            ('AUTO', "Auto", "Infer the face plane from the first two different movement axes"),
            ('XY', "XY", "Draw parallel to the XY plane"),
            ('XZ', "XZ", "Draw parallel to the XZ plane"),
            ('YZ', "YZ", "Draw parallel to the YZ plane"),
            ('FACE', "Face", "Draw on a local workplane captured from a mesh face"),
        ),
        default='XY',
    )
    workplane_u: FloatVectorProperty(size=3, subtype='DIRECTION', default=(1.0, 0.0, 0.0), options={'HIDDEN'})
    workplane_v: FloatVectorProperty(size=3, subtype='DIRECTION', default=(0.0, 1.0, 0.0), options={'HIDDEN'})
    workplane_normal: FloatVectorProperty(size=3, subtype='DIRECTION', default=(0.0, 0.0, 1.0), options={'HIDDEN'})
    auto_axis_threshold: IntProperty(
        name="Auto gesture",
        description="Continuous mouse distance required to accept each axis in Automatic face orientation",
        default=18,
        min=4,
        max=64,
        subtype='PIXEL',
    )
    grid_snap: BoolProperty(
        name="Incremental",
        description="Quantize creation, movement, and extrusion using ShapeFlow's configured step",
        default=True,
    )
    geometry_snap: BoolProperty(
        name="Magnetic",
        description="Snap directly to nearby vertices, edges, midpoints, and face centers",
        default=True,
    )
    smart_guides: BoolProperty(
        name="Smart guides",
        description="Align creation points with nearby geometry even when the pointer is not directly over it",
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
        items=active_tool_items(),
        default='NONE',
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    bpy.types.WindowManager.shapeflow_polygon_mode = EnumProperty(
        name="Polygon mode",
        items=(('VERTEX', "Regular by vertex", "Radius reaches a vertex"),
               ('EDGE', "Regular by edge", "Radius reaches the midpoint of an edge"),
               ('FREE', "Free vertices", "Place each vertex independently")),
        default='VERTEX', options={'SKIP_SAVE'},
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
    del bpy.types.WindowManager.shapeflow_polygon_mode
    del bpy.types.WindowManager.shapeflow_workspace
    del bpy.types.WindowManager.shapeflow_mode
    del bpy.types.Scene.shapeflow
