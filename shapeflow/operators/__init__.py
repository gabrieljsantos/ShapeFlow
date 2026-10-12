from .draw_profile import SHAPEFLOW_OT_draw_rectangle
from .draw_stroke import SHAPEFLOW_OT_draw_stroke
from .bevel_edge import SHAPEFLOW_OT_bevel_edge
from .boolean import SHAPEFLOW_OT_boolean
from .draw_polygon import SHAPEFLOW_OT_draw_polygon, SHAPEFLOW_OT_polygon_settings
from .draw_advanced import SHAPEFLOW_OT_draw_advanced
from .draw_dimensional import SHAPEFLOW_OT_draw_dimensional
from .curve_edit import SHAPEFLOW_OT_curve_edit
from .extrude_face import SHAPEFLOW_OT_extrude_face
from .follow_me import SHAPEFLOW_OT_follow_me
from .offset_face import SHAPEFLOW_OT_offset_face
from .organization import SHAPEFLOW_OT_combine_objects, SHAPEFLOW_OT_component, SHAPEFLOW_OT_group_objects, SHAPEFLOW_OT_separate_object
from .repetition import SHAPEFLOW_OT_copy_series, SHAPEFLOW_OT_mirror
from .mode import SHAPEFLOW_OT_activate_tool, SHAPEFLOW_OT_toggle_mode
from .spatial import SHAPEFLOW_OT_move_object
from .solid_tools import SHAPEFLOW_OT_solid_tool
from .solid_inspector import SHAPEFLOW_OT_solid_inspector
from .transform_object import SHAPEFLOW_OT_transform_object
from .rotate_precise import SHAPEFLOW_OT_rotate_precise
from .workplane import SHAPEFLOW_OT_pick_workplane

CLASSES = (
    SHAPEFLOW_OT_draw_rectangle,
    SHAPEFLOW_OT_draw_stroke,
    SHAPEFLOW_OT_bevel_edge,
    SHAPEFLOW_OT_boolean,
    SHAPEFLOW_OT_polygon_settings,
    SHAPEFLOW_OT_draw_polygon,
    SHAPEFLOW_OT_draw_advanced,
    SHAPEFLOW_OT_draw_dimensional,
    SHAPEFLOW_OT_curve_edit,
    SHAPEFLOW_OT_extrude_face,
    SHAPEFLOW_OT_follow_me,
    SHAPEFLOW_OT_offset_face,
    SHAPEFLOW_OT_group_objects,
    SHAPEFLOW_OT_combine_objects,
    SHAPEFLOW_OT_separate_object,
    SHAPEFLOW_OT_component,
    SHAPEFLOW_OT_copy_series,
    SHAPEFLOW_OT_mirror,
    SHAPEFLOW_OT_toggle_mode,
    SHAPEFLOW_OT_activate_tool,
    SHAPEFLOW_OT_move_object,
    SHAPEFLOW_OT_solid_tool,
    SHAPEFLOW_OT_solid_inspector,
    SHAPEFLOW_OT_transform_object,
    SHAPEFLOW_OT_rotate_precise,
    SHAPEFLOW_OT_pick_workplane,
)
